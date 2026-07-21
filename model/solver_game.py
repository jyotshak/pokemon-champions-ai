"""EngineGame: adapts (engine bridge x action enumeration x
determinizations) into the game protocol ExternalSamplingSolver consumes,
plus solve_decision(), the one-call entry point for a real turn decision.

The bridge is INJECTED and duck-typed (init_battle/step/free with
engine/bridge.py's signatures) — model/ never imports engine/, per the
dependency rule; anything satisfying the interface (a fake, a worker
pool later) slots in.

Infoset keys (docs/solver_design.md 2.1):
- my_key: the public-observation snapshot — my side fully, the
  opponent's VISIBLE facts only (actives' species/position/%hp/status/
  boosts/volatiles/mega, living-bench count, field). Opponent HP enters
  as a rounded percentage, not exact points: exact HP would leak the
  world's hidden spread hypothesis into my key and re-open the strategy
  fusion hole the shared table exists to close. World-independent by
  construction.
- opp_key: (world id, full state) — they know everything about
  themselves.

solve_decision returns the argmax of the root average strategy (strongest
vs a non-adapting opponent; sampling from the mixed strategy instead is
the right call against adapting opponents — parked as an open question).
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Hashable, NamedTuple, Optional

from model.action_space import propose_pruned_team_preview_actions, propose_pruned_turn_actions
from model.leaf_value import hp_leaf_value
from model.mccfr import ExternalSamplingSolver
from model.regret import RegretNode
from schema.battle_state import MoveAction, OwnPokemon, SwitchAction, TeamPreviewAction, TurnActions
from schema.full_info_state import FullInfoState, TeamPreviewRootState, bench_mons


class _Node(NamedTuple):
    world: int
    handle: Optional[int]
    state: FullInfoState
    terminal: Optional[float]


def _mon_public(mon: OwnPokemon, own_side: bool) -> tuple:
    boosts = mon.boosts
    common = (
        mon.species, mon.position, mon.fainted, mon.status,
        (boosts.atk, boosts.defense, boosts.spa, boosts.spd, boosts.spe, boosts.acc, boosts.eva),
        mon.mega_activated, mon.trapped,
    )
    # trapped MUST be in the key (unlike opponent volatiles, which were
    # deliberately dropped): it directly changes the legal action set
    # (switch offered or not), and the solver's keying contract requires
    # a key to fully determine its action set - omitting it would trade
    # the my_key-mismatch crash for an n_actions-mismatch crash instead.
    # One accepted subtlety this reopens: if trapped depends on an
    # opponent's still-unrevealed ability (Arena Trap et al.), it can
    # legitimately differ across determinization worlds - unlike
    # mega_used/boosts (reconstruction bugs corrected earlier), this
    # isn't a bug to fix, it's a genuine fact a real player in that
    # situation wouldn't know either (mirrors Showdown's own
    # trapped/maybeTrapped distinction). Accepted for now rather than
    # building a richer tri-state representation.
    if own_side:
        return common + (
            mon.hp, mon.item, tuple((ms.move, ms.pp, ms.disabled) for ms in mon.moves),
            tuple(sorted(v.name for v in mon.volatiles)),
        )
    # opponent: rounded percent, never exact points (see module docstring).
    # Volatiles deliberately excluded here (known v1 simplification, unlike
    # everything else in `common` which the real protocol always announces):
    # some held items/abilities attach a persistent bookkeeping volatile
    # (e.g. Metronome-the-item's consecutive-move tracker) the instant
    # they're equipped, purely as engine-internal state, not something a
    # real opponent could observe. Since the item causing it is exactly
    # the kind of hidden fact that varies between determinization worlds,
    # including volatiles here re-opened the world-independence hole the
    # keying contract exists to close (whichever world happened to sample
    # that item onto this mon would silently diverge the key). A name
    # whitelist would be more precise but requires knowing every such
    # engine-internal volatile in advance; dropping opponent volatiles
    # from the key entirely is the safe default until concrete search
    # quality issues justify building that whitelist. Costs some
    # regret-table granularity (e.g. confused vs not doesn't split nodes
    # for opponent-side bucketing) — not a soundness issue, since the
    # simulated STATE still has real volatiles; only the key used to
    # bucket regret tables is coarsened.
    hp_pct = int(round(100 * mon.hp / mon.max_hp)) if mon.max_hp else 0
    return common + (hp_pct,)


def _field_key(state: FullInfoState) -> tuple:
    f = state.field
    sides = []
    for sc in (f.my_side, f.opp_side):
        sides.append((
            sc.reflect_turns, sc.light_screen_turns, sc.aurora_veil_turns, sc.tailwind_turns,
            sc.safeguard_turns, sc.mist_turns, sc.stealth_rock, sc.spikes_layers,
            sc.toxic_spikes_layers, sc.sticky_web, sc.mega_used,
        ))
    return (f.weather, f.weather_turns, f.terrain, f.terrain_turns,
            f.trick_room_turns, f.gravity_turns, tuple(sides))


def _public_key(state: FullInfoState) -> tuple:
    opp_active = tuple(
        _mon_public(m, own_side=False) for m in state.opp_team if m.position is not None
    )
    opp_bench_alive = sum(1 for m in state.opp_team if m.position is None and not m.fainted)
    return (
        state.turn,
        tuple(_mon_public(m, own_side=True) for m in state.my_team),
        opp_active,
        opp_bench_alive,
        _field_key(state),
    )


def _full_key(state: FullInfoState) -> tuple:
    # Volatiles are safe to include here (unlike _mon_public's opponent
    # path): opp_key is always prefixed with world_id by the caller, so
    # there is no cross-world collision to guard against — within one
    # already-pinned world, a mon's volatiles (however they arose) are
    # exactly known and legitimately part of what the opponent conditions
    # on.
    opp_hidden = tuple(
        (m.species, m.item, m.ability, m.hp,
         tuple((ms.move, ms.pp, ms.disabled) for ms in m.moves),
         tuple(sorted(m.stats.items())),
         tuple(sorted(v.name for v in m.volatiles)))
        for m in state.opp_team
    )
    return _public_key(state) + (opp_hidden,)


def _self_switch_targets(actions: TurnActions) -> list[int]:
    """Bench indices any self-switch MoveAction (Parting Shot etc. - see
    MoveAction.switch_bench_slot) in this TurnActions wants to bring in,
    LEFT before RIGHT - matches the order the real engine's own forced-
    switch auto-pick processes flagged active slots (Side.getChoiceIndex
    walks index 0 then 1), so a caller can use this list directly as
    _reorder_bench's priority order.
    """
    targets = []
    for action in (actions.slot_left, actions.slot_right):
        if isinstance(action, MoveAction) and action.switch_bench_slot is not None:
            targets.append(action.switch_bench_slot)
    return targets


def _reorder_bench(team: list[OwnPokemon], priority: list[int]) -> tuple[list[OwnPokemon], dict[int, int]]:
    """Returns (reordered team, old_bench_index -> new_bench_index), with
    `priority`'s bench_mons() indices moved to the front in the given
    order. This is the whole mechanism behind resolving a self-switch
    move's destination with zero engine changes: the real engine's own
    forced-switch auto-pick (Side.chooseSwitch() called with no slot -
    vendor/pokemon-showdown/sim/side.ts) always takes the lowest-index
    living, not-yet-claimed bench mon in side.pokemon array order, which
    is exactly the order init_battle hands the engine - so reordering
    the INPUT team before a fresh init_battle deterministically steers
    which bench mon the engine picks, with no protocol change to
    engine/bridge.js at all. Actives are identified by their own
    .position field downstream, not list order, so only the bench
    sublist's relative order needs to change.

    Fainted bench mons are kept, appended after the reordered living
    ones - NOT dropped. bench_mons() is living-only by design (matches
    what SwitchAction.bench_slot indexes everywhere else), but the
    output here is a full replacement TEAM for a fresh init_battle call:
    silently shrinking the roster (found live, several turns into a real
    search tree, once something had actually fainted) desyncs every
    downstream index against the pre-reorder team the rest of this turn's
    actions were built against, corrupting the fresh reconstruction.
    """
    actives = [m for m in team if m.position is not None]
    bench = bench_mons(team)
    fainted_bench = [m for m in team if m.position is None and m.fainted]
    remaining = [i for i in range(len(bench)) if i not in priority]
    new_order = priority + remaining  # bench[new_order[k]] ends up at new index k
    remap = {old_i: new_i for new_i, old_i in enumerate(new_order)}
    return actives + [bench[i] for i in new_order] + fainted_bench, remap


def _remap_switches(actions: TurnActions, remap: dict[int, int]) -> TurnActions:
    """Translate any plain SwitchAction's bench_slot through `remap` -
    needed only when the SAME side also reorders its bench for a self-
    switch move elsewhere in this same joint turn, so the two stay
    mutually consistent. A self-switch MoveAction's own switch_bench_slot
    never needs remapping here: it's never read for choice-string
    construction (only "move N [target] [mega]" is sent - see
    engine/bridge.py::_slot_choice), only to decide the reorder itself
    (_self_switch_targets), which already happened before this is called.
    """
    def fix(action):
        if isinstance(action, SwitchAction):
            return action.model_copy(update={"bench_slot": remap[action.bench_slot]})
        return action
    return TurnActions(slot_left=fix(actions.slot_left), slot_right=fix(actions.slot_right))


def _resolve_self_switches(
    bridge, handle: int, state: FullInfoState, my: TurnActions, opp: TurnActions, handles: list[int],
) -> tuple[int, FullInfoState, TurnActions, TurnActions]:
    """If `my`/`opp` includes a self-switch MoveAction, reorders the
    relevant side's bench (_reorder_bench) and gets a FRESH handle/state
    from the bridge via a real init_battle call, so the engine's own
    default forced-switch auto-pick lands on the intended mon - any
    OTHER plain SwitchAction on the SAME side this same turn gets its
    bench_slot translated through the same reorder (_remap_switches), so
    both choices stay correct together. New handles are appended to
    `handles` for the caller's existing free()-on-teardown bookkeeping.
    Falls through to the original (handle, state, my, opp) untouched
    when nothing needs reordering - the common case, zero extra engine
    calls.
    """
    my_targets = _self_switch_targets(my)
    opp_targets = _self_switch_targets(opp)
    if not my_targets and not opp_targets:
        return handle, state, my, opp
    my_team, opp_team = state.my_team, state.opp_team
    if my_targets:
        my_team, my_remap = _reorder_bench(state.my_team, my_targets)
        my = _remap_switches(my, my_remap)
    if opp_targets:
        opp_team, opp_remap = _reorder_bench(state.opp_team, opp_targets)
        opp = _remap_switches(opp, opp_remap)
    reordered = state.model_copy(update={"my_team": my_team, "opp_team": opp_team})
    new_handle, echo = bridge.init_battle(reordered)
    handles.append(new_handle)
    return new_handle, echo, my, opp


class EngineGame:
    def __init__(self, bridge, root_states: list[FullInfoState], per_slot_cap: int = 6):
        self._bridge = bridge
        self._cap = per_slot_cap
        self.handles: list[int] = []
        self.step_count = 0
        self.error_count = 0
        self._roots: list[_Node] = []
        for world_id, state in enumerate(root_states):
            handle, echo = bridge.init_battle(state)
            self.handles.append(handle)
            self._roots.append(_Node(world_id, handle, echo, None))

    def worlds(self):
        # determinizations are sampled i.i.d. from the belief, so equal weights
        return [(node, 1.0 / len(self._roots)) for node in self._roots]

    def is_terminal(self, node: _Node) -> Optional[float]:
        return node.terminal

    def leaf_value(self, node: _Node) -> float:
        return hp_leaf_value(node.state)

    def my_actions(self, node: _Node) -> list[TurnActions]:
        return propose_pruned_turn_actions(node.state, "me", self._cap)

    def opp_actions(self, node: _Node) -> list[TurnActions]:
        return propose_pruned_turn_actions(node.state, "opp", self._cap)

    def step(self, node: _Node, my: TurnActions, opp: TurnActions, rng: random.Random) -> _Node:
        # rng unused: the bridge reseeds the engine RNG per step, which is
        # exactly the fresh-chance-per-sample behavior MCCFR wants
        handle, state, my, opp = _resolve_self_switches(
            self._bridge, node.handle, node.state, my, opp, self.handles,
        )
        result = self._bridge.step(handle, state, my, opp)
        self.step_count += 1
        self.error_count += len(result.errors)
        if result.handle is not None:
            self.handles.append(result.handle)
        return _Node(node.world, result.handle, result.state, result.terminal)

    def my_key(self, node: _Node) -> tuple:
        return _public_key(node.state)

    def opp_key(self, node: _Node) -> tuple:
        return (node.world,) + _full_key(node.state)


class TeamPreviewGame:
    """Sibling of EngineGame for the team-preview decision, NOT a
    modification of it: its step()/my_key/opp_key are turn-specific by
    construction (bridge.step() drives one Showdown turn; my_key/opp_key
    read FullInfoState fields like turn/boosts/field-side-condition-turns
    that don't exist pre-battle), so a genuinely different root action
    (bring/lead instead of move/switch) needs its own adapter.

    Nodes are heterogeneous by depth, dispatched via isinstance: depth 0
    (root) carries a TeamPreviewRootState (the full 6-mon pool, nobody
    active); depth >=1 carries a real FullInfoState (team preview has
    resolved into a genuine in-battle position). model/mccfr.py needs
    ZERO changes for this - ExternalSamplingSolver only ever calls
    game.* methods and has no notion of what a "level" represents
    structurally, so dispatching on state shape inside each of the six
    methods is enough to compose two structurally different decision
    types into one search tree.

    Confirmed design (docs/solver_design.md, team preview section):
    depth_limit=2 - team preview resolves at depth 1 (through the real
    engine, so send-out effects like Intimidate/Drizzle actually fire),
    then a real turn-1 move exchange resolves at depth 2, where
    hp_leaf_value cuts. This is deliberate, not a shortcut: scoring
    immediately after send-out (depth_limit=1) can't see HP-based damage
    yet and would not catch the bug that motivated building this at all
    (a bad lead pair only actually loses HP once a move is exchanged).
    """

    def __init__(self, bridge, root_states: list[TeamPreviewRootState],
                 tp_bring_cap: int = 6, tp_lead_cap: int = 2, turn_cap: int = 6,
                 synergy_weights: Optional[dict] = None, synergy_scale: float = 1.0,
                 mega_penalty: float = 0.0):
        self._bridge = bridge
        self._tp_bring_cap = tp_bring_cap
        self._tp_lead_cap = tp_lead_cap
        self._turn_cap = turn_cap
        self._synergy_weights = synergy_weights
        self._synergy_scale = synergy_scale
        self._mega_penalty = mega_penalty
        self.handles: list[int] = []
        self.step_count = 0
        self.error_count = 0
        self._roots: list[_Node] = []
        for world_id, state in enumerate(root_states):
            handle = bridge.init_team_preview_battle(state)
            self.handles.append(handle)
            # root node's .state is the ORIGINAL Python-built
            # TeamPreviewRootState, not an engine echo - unlike
            # init_battle, nothing here was mutated/recomputed (the fresh
            # battle is paused exactly at teampreview, untouched), so the
            # Python object we built already is what we intend.
            self._roots.append(_Node(world_id, handle, state, None))

    def worlds(self):
        return [(node, 1.0 / len(self._roots)) for node in self._roots]

    def is_terminal(self, node: _Node) -> Optional[float]:
        return node.terminal

    def leaf_value(self, node: _Node) -> float:
        # Only ever reached at depth>=1 (a real FullInfoState) given
        # depth_limit>=1 - see class docstring.
        return hp_leaf_value(node.state)

    def my_actions(self, node: _Node):
        if isinstance(node.state, TeamPreviewRootState):
            return propose_pruned_team_preview_actions(
                node.state, "me", self._tp_bring_cap, self._tp_lead_cap,
                self._synergy_weights, self._synergy_scale, self._mega_penalty,
            )
        return propose_pruned_turn_actions(node.state, "me", self._turn_cap)

    def opp_actions(self, node: _Node):
        if isinstance(node.state, TeamPreviewRootState):
            return propose_pruned_team_preview_actions(
                node.state, "opp", self._tp_bring_cap, self._tp_lead_cap,
                self._synergy_weights, self._synergy_scale, self._mega_penalty,
            )
        return propose_pruned_turn_actions(node.state, "opp", self._turn_cap)

    def step(self, node: _Node, my, opp, rng: random.Random) -> _Node:
        if isinstance(node.state, TeamPreviewRootState):
            result = self._bridge.step_team_preview(node.handle, my, opp)
        else:
            handle, state, my, opp = _resolve_self_switches(
                self._bridge, node.handle, node.state, my, opp, self.handles,
            )
            result = self._bridge.step(handle, state, my, opp)
        self.step_count += 1
        self.error_count += len(result.errors)
        if result.handle is not None:
            self.handles.append(result.handle)
        return _Node(node.world, result.handle, result.state, result.terminal)

    def my_key(self, node: _Node) -> tuple:
        # Unchanged from EngineGame - _public_key only ever touches
        # turn/field/my_team/opp_team structurally, which both
        # TeamPreviewRootState and FullInfoState share. state.turn itself
        # (0 at the root, 1+ once team preview resolves) already keeps
        # root nodes and post-resolution nodes from ever colliding.
        return _public_key(node.state)

    def opp_key(self, node: _Node) -> tuple:
        return (node.world,) + _full_key(node.state)


class SolveDiagnostics(NamedTuple):
    strategy: list[tuple[TurnActions, float]]  # root actions with probabilities, best first
    step_count: int
    error_count: int


def solve_decision(
    bridge,
    root_states: list[FullInfoState],
    iterations: int = 80,
    depth_limit: int = 1,
    per_slot_cap: int = 6,
    rng: Optional[random.Random] = None,
) -> tuple[TurnActions, SolveDiagnostics]:
    game = EngineGame(bridge, root_states, per_slot_cap)
    solver = ExternalSamplingSolver(game, depth_limit=depth_limit, rng=rng)
    strategy = solver.run(iterations)
    actions = solver.root_actions()
    ranked = sorted(zip(actions, strategy), key=lambda pair: -pair[1])
    bridge.free(game.handles)
    return ranked[0][0], SolveDiagnostics(
        strategy=ranked, step_count=game.step_count, error_count=game.error_count,
    )


def _merge_regret_tables(tables: list[dict[Hashable, RegretNode]]) -> dict[Hashable, RegretNode]:
    """Sum several independent partial solves' regret tables into one.
    Standard CFR parallelization (docs/solver_design.md): summing
    cumulative regret/strategy across N workers that each ran a fraction
    of the iterations from the SAME root is the established way large-
    scale CFR solvers parallelize — a well-precedented approximation of
    running all iterations sequentially against one shared table, not a
    shortcut. Requires all workers to have solved the identical
    root_states (same content -> same keys, regardless of which bridge
    process computed them), so matching keys are directly comparable.
    """
    merged: dict[Hashable, RegretNode] = {}
    for table in tables:
        for key, node in table.items():
            target = merged.get(key)
            if target is None:
                target = RegretNode(node.n_actions)
                merged[key] = target
            elif target.n_actions != node.n_actions:
                raise ValueError(
                    f"merge mismatch at {key!r}: {target.n_actions} vs {node.n_actions} actions - "
                    "workers did not solve identical root_states"
                )
            for i in range(node.n_actions):
                target.cumulative_regret[i] += node.cumulative_regret[i]
                target.cumulative_strategy[i] += node.cumulative_strategy[i]
    return merged


def _solve_worker(
    bridge, root_states: list[FullInfoState], iterations: int, depth_limit: int,
    per_slot_cap: int, rng: random.Random, traverser_offset: int,
) -> tuple[ExternalSamplingSolver, EngineGame]:
    game = EngineGame(bridge, root_states, per_slot_cap)
    solver = ExternalSamplingSolver(game, depth_limit=depth_limit, rng=rng)
    solver.run(iterations, traverser_offset=traverser_offset)
    return solver, game


def solve_decision_parallel(
    pool,  # EngineBridgePool — duck-typed (exposes .bridges), model/ never imports engine/
    root_states: list[FullInfoState],
    iterations: int = 80,
    depth_limit: int = 1,
    per_slot_cap: int = 6,
    rng: Optional[random.Random] = None,
) -> tuple[TurnActions, SolveDiagnostics]:
    """Same contract as solve_decision, but splits `iterations` across
    pool.bridges, runs the resulting independent partial solves
    concurrently (each worker gets its own EngineGame/bridge — no
    cross-process snapshot sharing needed, since every worker
    reconstructs the identical root_states itself), and merges their
    regret tables. Needs zero changes to engine/bridge.js or the core
    MCCFR algorithm — this is purely a Python-side orchestration layer.
    """
    rng = rng or random.Random()
    n_workers = len(pool.bridges)
    base, extra = divmod(iterations, n_workers)
    counts = [base + (1 if i < extra else 0) for i in range(n_workers)]

    results: list[Optional[tuple[ExternalSamplingSolver, EngineGame]]] = [None] * n_workers
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = {
            ex.submit(
                _solve_worker, pool.bridges[i], root_states, counts[i], depth_limit,
                per_slot_cap, random.Random(rng.random()), i % 2,
            ): i
            for i in range(n_workers) if counts[i] > 0
        }
        for future, i in futures.items():
            results[i] = future.result()

    active = [(i, r) for i, r in enumerate(results) if r is not None]
    merged_my = _merge_regret_tables([solver.my_nodes for _, (solver, _) in active])
    first_solver = active[0][1][0]
    strategy = merged_my[first_solver.root_key].average_strategy()
    actions = first_solver.root_actions()  # identical across workers: identical root_states

    total_steps = sum(game.step_count for _, (_, game) in active)
    total_errors = sum(game.error_count for _, (_, game) in active)
    for i, (_, game) in active:
        pool.bridges[i].free(game.handles)

    ranked = sorted(zip(actions, strategy), key=lambda pair: -pair[1])
    return ranked[0][0], SolveDiagnostics(
        strategy=ranked, step_count=total_steps, error_count=total_errors,
    )


def solve_team_preview_decision(
    bridge,
    root_states: list[TeamPreviewRootState],
    iterations: int = 32,
    depth_limit: int = 2,
    tp_bring_cap: int = 6,
    tp_lead_cap: int = 2,
    turn_cap: int = 6,
    synergy_weights: Optional[dict] = None,
    synergy_scale: float = 1.0,
    mega_penalty: float = 0.0,
    rng: Optional[random.Random] = None,
) -> tuple[TeamPreviewAction, SolveDiagnostics]:
    """Same shape as solve_decision, over TeamPreviewGame instead of
    EngineGame. depth_limit=2 by default - see TeamPreviewGame's
    docstring for why depth_limit=1 would not catch the bug this feature
    exists to fix. synergy_weights/mega_penalty default to inert (None/
    0.0) - callers (harness/) inject the real belief-layer table for live
    play.
    """
    game = TeamPreviewGame(bridge, root_states, tp_bring_cap, tp_lead_cap, turn_cap,
                            synergy_weights, synergy_scale, mega_penalty)
    solver = ExternalSamplingSolver(game, depth_limit=depth_limit, rng=rng)
    strategy = solver.run(iterations)
    actions = solver.root_actions()
    ranked = sorted(zip(actions, strategy), key=lambda pair: -pair[1])
    bridge.free(game.handles)
    return ranked[0][0], SolveDiagnostics(
        strategy=ranked, step_count=game.step_count, error_count=game.error_count,
    )


def _solve_team_preview_worker(
    bridge, root_states: list[TeamPreviewRootState], iterations: int, depth_limit: int,
    tp_bring_cap: int, tp_lead_cap: int, turn_cap: int,
    synergy_weights: Optional[dict], synergy_scale: float, mega_penalty: float,
    rng: random.Random, traverser_offset: int,
) -> tuple[ExternalSamplingSolver, TeamPreviewGame]:
    game = TeamPreviewGame(bridge, root_states, tp_bring_cap, tp_lead_cap, turn_cap,
                            synergy_weights, synergy_scale, mega_penalty)
    solver = ExternalSamplingSolver(game, depth_limit=depth_limit, rng=rng)
    solver.run(iterations, traverser_offset=traverser_offset)
    return solver, game


def solve_team_preview_decision_parallel(
    pool,
    root_states: list[TeamPreviewRootState],
    iterations: int = 32,
    depth_limit: int = 2,
    tp_bring_cap: int = 6,
    tp_lead_cap: int = 2,
    turn_cap: int = 6,
    synergy_weights: Optional[dict] = None,
    synergy_scale: float = 1.0,
    mega_penalty: float = 0.0,
    rng: Optional[random.Random] = None,
) -> tuple[TeamPreviewAction, SolveDiagnostics]:
    """Same contract/shape as solve_decision_parallel, over
    TeamPreviewGame. _merge_regret_tables is reused completely unchanged
    - it only ever operates on dict[Hashable, RegretNode], agnostic to
    what the keys/actions represent.
    """
    rng = rng or random.Random()
    n_workers = len(pool.bridges)
    base, extra = divmod(iterations, n_workers)
    counts = [base + (1 if i < extra else 0) for i in range(n_workers)]

    results: list[Optional[tuple[ExternalSamplingSolver, TeamPreviewGame]]] = [None] * n_workers
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = {
            ex.submit(
                _solve_team_preview_worker, pool.bridges[i], root_states, counts[i], depth_limit,
                tp_bring_cap, tp_lead_cap, turn_cap, synergy_weights, synergy_scale, mega_penalty,
                random.Random(rng.random()), i % 2,
            ): i
            for i in range(n_workers) if counts[i] > 0
        }
        for future, i in futures.items():
            results[i] = future.result()

    active = [(i, r) for i, r in enumerate(results) if r is not None]
    merged_my = _merge_regret_tables([solver.my_nodes for _, (solver, _) in active])
    first_solver = active[0][1][0]
    strategy = merged_my[first_solver.root_key].average_strategy()
    actions = first_solver.root_actions()

    total_steps = sum(game.step_count for _, (_, game) in active)
    total_errors = sum(game.error_count for _, (_, game) in active)
    for i, (_, game) in active:
        pool.bridges[i].free(game.handles)

    ranked = sorted(zip(actions, strategy), key=lambda pair: -pair[1])
    return ranked[0][0], SolveDiagnostics(
        strategy=ranked, step_count=total_steps, error_count=total_errors,
    )
