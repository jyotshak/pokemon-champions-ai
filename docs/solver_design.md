# Solver Design — decisions and status

Living document for the decision-making model (the "logic layer") and the
belief/"meta" layer that feeds it. Records every design decision made so
far, with rationale, plus an implementation checklist. **Update this
whenever a decision is made or a checklist item lands** — it is the
canonical record that survives conversation compaction and time away.

Last updated: 2026-07-20 — **major direction change: the replay-trained
policy/value net is now the primary solver; the MCCFR tree is the
baseline/reference opponent.** See the new §6 for the whole net track
(replay pipeline, encoder, network, training results, depth-1 search,
live player, measured results, and the planned improvements). Tier-1
type pruning also landed on the tree side (§2.12), which is what made
depth 3 affordable and, in doing so, produced the evidence that depth
was NOT the bottleneck — motivating the pivot.

Previously (2026-07-18): search-based team preview built end to end -
see §2.8 - fixing a confirmed deterministic bad-lead bug found via a
non-mirror-match test batch; team-synergy + mega-usage scoring added on
top, §2.9, blending real Pikalytics teammate/team-core data into both
team-preview scoring consumers; two more forced-switch stuck-loop bugs
found+fixed live, §2.10; parallel engine pool built earlier the same
day, 3.8x measured speedup with 8 workers, wired into SolverPlayer;
self-switch moves upgraded from a static "first bench mon" heuristic to
real search, §2.11, fixing the Swampert-over-Pelipper mispick found via
the same forced-lead diagnostic batch - live play also got a damage-
aware forced-switch fallback for the still-heuristic KO-triggered case)

---

## 1. Big picture

Goal: professional-level play of Pokemon Champions doubles (Reg M-B, Bo1,
closed team sheets), reasoning correctly under hidden information and
randomness. Two downstream products reuse the same core model unchanged:
a post-hoc replay analyzer ("best move at every turn including team
preview") and a live BlueStacks assistant (CNN reads the screen, model
suggests, user clicks).

Layering (dependency direction is enforced, see repo layout):

```
schema/   the contract (BattleState, actions). No dependencies.
model/    decision-making core. Depends only on schema/ + reference/ data.
belief/   the "meta layer". Depends only on schema/ + reference/.
harness/  poke-env / local-Showdown glue. The only place poke-env imports live.
engine/   (planned) Node child-process bridge to Showdown's Sim.Battle for
          search rollouts. Showdown-specific, sibling of harness/, model/
          only ever sees its abstract step() interface.
```

### Two-layer split: meta layer vs logic layer

- **Meta layer (belief/)**: owns "what is the opponent likely running" —
  team-archetype priors, per-mon move/item/ability/spread distributions,
  cross-mon correlations. This is the only layer that needs retraining
  when the legal pool / usage meta shifts.
- **Logic layer (model/)**: owns "given those beliefs, what is the optimal
  play". Game-theory + search. Meta-independent once in game: a banlist
  change never invalidates it.

Interface between them: `sample_determinization(observed_facts) ->
FullInfoState`. One call returns ONE complete, internally-coherent
hypothesis of the opponent's side. All correlation logic (mega-pairing
exclusivity, "Basculegion is almost always brought so if unseen it's in
the back", Calm Mind => Draining Kiss not Light of Ruin) lives INSIDE
the sampler. The logic layer never touches marginals directly — sampling
fields independently from marginals would silently break exactly those
correlations. Marginal `WeightedOption` lists remain as a side channel
for logging/explainability only.

The meta layer will eventually expose `initialize(team_preview)` +
`update(revealed_fact)`; the logic layer just consumes the current
distribution each turn and doesn't care whether updates are cheap
Bayesian conditioning or full re-inference.

## 2. Logic-layer architecture: ReBeL-style depth-limited CFR

**Chosen**: re-solve at every real decision point with depth-limited
counterfactual regret minimization over belief states, ReBeL-style
("Recursive Belief-based Learning", Brown et al. 2020). A value network
(later; heuristic placeholder now) evaluates depth-cutoff leaves, a
policy network (later) prunes action candidates.

**Rejected alternatives and why**:
- Plain PPO self-play policy: viable fallback, but search + re-solving is
  the stronger architecture for a game this short (~8 turns average) and
  this hidden-info-heavy; user prioritized strength over cost.
- Minimax / vanilla MCTS: assumes sequential moves. Doubles turns are
  SIMULTANEOUS commits — sequential solvers produce exploitable pure
  strategies at Protect/no-Protect style mindgame nodes. Regret matching
  at simultaneous-move matrix nodes converges to a mixed equilibrium.

**One-sided simplification (v1, deliberate)**: we model the opponent as
knowing OUR exact set (no second-order "their uncertainty about us").
Rationale: good human opponents mostly do know likely sets; we want
optimal play, not surprise value. Halves the modeling complexity.
Revisit only after the simple version works.

### 2.1 Determinization + multi-world regret sharing

Per real decision: draw K determinizations (complete opponent
hypotheses) from the meta layer, run CFR across ALL of them jointly,
output the time-averaged root strategy, sample/argmax the real action.

**Strategy-fusion trap (the key correctness constraint)**: solving each
world independently and averaging afterward implicitly lets the solver
act differently per hidden world — an incoherent "plan" no single agent
can execute. Fix: MY regret tables are keyed by public information only
and shared across all K worlds; every world's counterfactual values
accumulate into the same table, weighted by world probability. This is
what produces genuine hedging (good in one world, not terrible in the
other) instead of blind averaging.

**Node keying asymmetry** (consequence of the one-sided simplification):
- My decision nodes: keyed by public information only. Shared across
  worlds.
- Opponent decision nodes: key includes their private info (world id).
  They know their own set; their legal actions literally differ per
  world.

**Keying contract (refined during implementation)**: keys are supplied
by the game object, and a key must fully determine its legal action set
(the solver raises on violations). For the real game this means keying
my nodes on the PUBLIC OBSERVATION SNAPSHOT (my side's full state + the
opponent's public state: species/HP%/status/revealed facts + field),
not raw action history — my action set is a function of exactly that
public info, and observation-keying also un-folds the chance
approximation we originally accepted (crit vs no-crit produce different
observations, hence different nodes, created lazily only when visited).
Nodes at the same observation reached via different histories merge —
a mild, standard infoset coarsening (loses some world-posterior nuance;
acceptable, and cheap to revisit by appending history digests to the
key).

### 2.2 Tree traversal: external-sampling MCCFR

Full expansion is impossible (~225 joint actions/side => ~50k cells per
node, squared per extra depth level). Per iteration:
- Pick one side as traverser (alternate each iteration).
- At traverser's nodes: enumerate ALL their actions (regret updates here).
- At the other side's nodes: sample ONE action from their current
  regret-matching strategy.
- At chance: sample — i.e. just let the engine roll its own RNG inside
  step(). Never enumerate engine randomness; MCCFR convergence is in
  expectation over iterations and the regret averaging denoises.

The `model/regret.py` core also has a full-expectation
`solve_matrix_game()` for small matrices (tests; possibly exact root
solves later).

### 2.3 Depth and recursion

- Depth unit = one full simultaneous turn = one engine `makeChoices`.
- Depth limit: start at 2 full turns, tune toward 3 if affordable.
- Terminal (game actually ends in-tree): exact ±1 (draw 0).
- Depth cutoff: leaf value function (below).
- **Forced mid-turn replacements**, two distinct triggers, two different
  treatments (§2.11 has the full story):
  - **Self-switching moves** (Parting Shot/U-turn/Volt Switch/Baton
    Pass/Flip Turn/Shed Tail/Chilly Reception): genuinely SEARCHED, not
    a shortcut — `MoveAction.switch_bench_slot` branches the move's own
    action space over every living bench mon, folded into the SAME
    turn-decision node (no new node, no engine changes, no tree-depth
    change: the bench reorder + real engine resolution happens inside
    `step()` itself). Superseded the original v1 shortcut described
    below, which only ever applied to this case.
  - **A mon fainting mid-resolution from an opponent's attack**: still
    the v1 shortcut — resolved INSIDE step() by the engine's own default
    forced-switch auto-pick (first living bench mon in team order,
    `resolveForcedSwitches` in `engine/bridge.js`), NOT a decision node.
    Not yet upgraded: unlike a self-switch move, whether MY mon faints
    depends on the OPPONENT's simultaneously-chosen action too, so it
    can't be enumerated as a fixed per-my-action branch the same way —
    an open problem, not addressed by §2.11.

### 2.4 Payoffs

Single scalar in [-1, +1] from our POV; zero-sum (opponent value = -v).

- Terminal: exactly ±1 regardless of margin (draw 0). No style bonus —
  margin bonuses make the solver spend win probability to win prettier.
- Leaf (depth cutoff), v1 placeholder:
  `v = (sum of my remaining HP fractions - sum of theirs) / 4`
  over the brought 4, fainted = 0. Same scale as terminals, so a certain
  win always outranks any cutoff position.
- Swappable single function `leaf_value(FullInfoState) -> float`. The
  eventual value net predicts win prob p and returns 2p - 1.
- Known v1 leaf blind spots (deliberately NOT hand-patched — the value
  net is supposed to learn these from self-play): all HP equally valued,
  status invisible, field state (Tailwind/Trick Room timers) invisible,
  all mons equally valued regardless of role.

### 2.5 Action space per node

Per slot, given a concrete (determinized) mon:
- Each move with pp > 0 × each legal target (from
  `reference/move_data.json` target field; spread/self/field moves don't
  branch on target).
- If the mon holds its own Mega Stone and side hasn't mega'd:
  each move branches mega=True/False (mega timing is a real decision).
- One SwitchAction per healthy bench mon.
- Fainted/absent slot: switch options ONLY.
- Joint action space = plain Cartesian product of the two slots (no
  cross-slot legality constraints; engine handles mid-turn redirection).

**Pruning seam**: enumeration goes behind `propose_actions(state, mon)`
so a policy net can later return top-K candidates instead of everything,
without restructuring node logic.

### 2.6 FullInfoState (search-node state)

NOT the meta layer — it's what one `sample_determinization()` call
produces: one concrete hypothesis with nothing hidden, so the real
engine can simulate it. Shape (reuses schema types, no new mon type):

- `turn: int`
- `field: FieldState` (always fully public)
- `my_team: list[OwnPokemon]` (active + bench)
- `opp_team: list[OwnPokemon]` — same OwnPokemon type as my side: after
  determinizing, their side is exactly as concrete as mine. Always 4
  mons: 2 revealed leads + 2 hypothesized back (the sampler picks WHICH
  2 of the 4 unseen species were brought, plus all hidden attributes for
  all 4).

No beliefs, no team_preview. Covers in-battle decisions only —
determinizing the team-preview decision itself (sampling whole opposing
rosters) is separate, later work.

### 2.7 Simulator (step function)

`step(state: FullInfoState, my_action: TurnActions, opp_action:
TurnActions) -> FullInfoState | TerminalResult`

Implementation: Showdown's real `Sim.Battle` driven in-process in a Node
child (JSON in/out) — verified against `vendor/pokemon-showdown/test/`
that `new Sim.Battle({format, p1: {team}, p2: {team}, seed})` +
`battle.makeChoices(p1str, p2str)` runs full battles synchronously with
no server/websocket, mid-battle state mutable, RNG seedable. Real engine
over a Python reimplementation: mechanics correctness is not something
to hand-approximate.

**Sequencing decision**: single engine instance first behind the
abstract interface; parallel worker pool later (embarrassingly parallel,
pure plumbing — the interface is what matters, and it's dictated by
solver usage patterns we learn first). Same logic applied twice more:
solver core built against a STUB step() before the real bridge; MCCFR
built before the determinizer so the consumer defines the producer's
contract.

### 2.8 Team preview

Was a placeholder (`model/heuristic.py::choose_team_preview`: bring
top-4 by base-stat-total, lead top-2 of those) used by BOTH players —
the search was never consulted for bring/lead, only in-battle turns.
This caused a real, confirmed bug (2026-07-18): a fixed placeholder lead
(two Steel-types, both 2x weak to Ground) got hit by a revealed
Garchomp's Earthquake for ~85% HP turn 1, identically in EVERY game
(team preview is deterministic — zero randomness), regardless of which
player piloted it — a 10-game solver-vs-heuristic batch swept 10/10 for
whichever side had the other team, telling us nothing about solver
quality.

**Now genuinely searched, composed onto the existing machinery rather
than needing new solver core**: `model/mccfr.py`'s `ExternalSamplingSolver`
is 100% generic over a duck-typed `game` object with no notion of what a
"level" represents structurally — so `model/solver_game.py::
TeamPreviewGame` (sibling of `EngineGame`, not a modification) dispatches
on node-state type: depth 0 carries a 6-mon `TeamPreviewRootState`
(`schema/full_info_state.py`), depth ≥1 carries a real `FullInfoState`,
reusing `propose_pruned_turn_actions`/`bridge.step`/`_public_key`/
`_full_key`/`hp_leaf_value` completely unchanged at that level.

**depth_limit=2, deliberately, not depth_limit=1**: team preview resolves
at depth 1 through the real engine (`engine/bridge.js`'s new
`init_team_preview`/`opInitTeamPreview` op — a genuinely fresh
`new Battle(...)`, paused exactly at the teampreview request, NOT the
mid-battle-reconstruction path `opInit` already had), so real send-out
effects (Intimidate, Drizzle, etc.) actually fire; a real turn-1 move
exchange then resolves at depth 2, where `hp_leaf_value` cuts. Confirmed
necessary, not just more thorough: scoring immediately post-send-out
(depth_limit=1) can't see HP-based damage yet, since Earthquake's damage
happens one step later — it would not have caught the bug that motivated
this work. Team-preview *submission* itself needed no new engine op:
Showdown's `side.choose()` already dispatches `"team NNNN"` choices
generically whenever `requestState === 'teampreview'`, so the
**existing, unmodified** `step`/`opStep` RPC handles it — confirmed
empirically (`engine/test_bridge_team_preview.py`) that the engine also
trims each side down to exactly the picked 4 once team preview resolves,
matching `FullInfoState`'s "always 4" contract.

**Determinizer** (`belief/determinize.py::sample_team_preview_world`):
my side needs no sampling at all — `state.my_bench` already holds all 6
of my own real `OwnPokemon` during `battle.in_team_preview` (nothing
active yet). Opponent side calls the existing `_fresh()` 6 times (not
4), one shared `used_items` set for the item clause. Deliberately does
NOT pre-sample which 4-of-6 the opponent brings — that's exactly the
action the opponent-side CFR search enumerates and mixes over, symmetric
to how in-battle search never pre-samples "what move will they pick."

**Pruning** (`model/action_space.py::propose_pruned_team_preview_actions`):
C(6,4)×12 = 180 raw joint actions per side is too many for engine-backed
search (matching why turn actions get pruned too). Two-stage: score all
15 bring-subsets by type-coverage offense minus defensive exposure
(`model/damage_calc.py`'s `type_effectiveness`/`species_types`, reading
ONLY species identity — never a world's sampled hidden attributes, the
same world-independence contract `my_key` already requires), keep the
top `bring_cap`; then pool ALL kept subsets' lead-pair candidates and
keep one GLOBAL top-(`bring_cap`×`lead_cap`) by the same scoring with
defense weighted higher (leads face the opponent's opener most
directly, including spread moves hitting both at once — the exact
mechanism of the reported bug). An earlier version scored top-`lead_cap`
independently PER kept subset instead of globally, which let even a
mediocre subset contribute its own "least-bad" pairs and still surface
the bad lead in one case — caught by the Archaludon+Metagross regression
test (`model/test_team_preview_actions.py`) before it ever reached the
engine.

**Cost**: measured, not assumed (`engine/test_team_preview_integration.py`)
— at realistic settings (`tp_bring_cap=6`, `tp_lead_cap=2`, `turn_cap=6`,
`n_worlds=3`) on an 8-worker pool: iterations=16 → 4,950 rollouts in
5.6s, iterations=24 → 7,260 rollouts in 6.1s, zero engine errors. Well
under the existing ~30-45s in-battle depth-2 turn-decision ballpark, as
hoped: team preview's pruned branching factor (≤12) is smaller than a
turn's (≤36), and it's a once-per-battle cost, not once-per-turn.

**Live validation** (`harness/solver_player.py`, `use_search_team_preview`,
default `True`): re-ran the exact scenario that exposed the bug
(`harness/teams.py`'s `TEAM_AERO_HO`/`TEAM_SWAMPERT_TR`, 5+5 games each
team assignment). The deterministic every-game bad-lead pattern is gone
— bring/lead now varies game to game (confirmed via saved logs: leads
alternate between Metagross+Swampert, Swampert+Pelipper, Pelipper+Swampert
across otherwise-identical games) and never repeats the Archaludon+
Metagross pair. Aero-side win rate dropped from a deterministic 10/10
sweep to 7/10 — the remaining losses reflect a real matchup/team-strength
difference now, not the mechanical bug this replaces.

### 2.9 Team-synergy + mega-usage scoring

Even with real search (§2.8), team-preview scoring only knew type-
coverage — a bring-4 that breaks up "always-brought-together" pairs
scored the same as one that didn't, and a subset with zero mega-eligible
members wasn't penalized. Added `model/team_preview_scoring.py`, a
shared leaf module used by BOTH `model/action_space.py`'s pruner and
`model/heuristic.py::choose_team_preview` (which is now genuinely
opponent-aware for the first time, not just gaining synergy/mega —
it shares the exact same `bring_subset_score`/`lead_pair_score` argmax
logic as the pruner at cap=1, instead of an independent top-4-BST sort).

**Two blended data sources**, combined into one symmetric pairwise table
(`belief/team_synergy.py::SYNERGY_WEIGHTS`, eager module-level constant,
same load-once convention as `species_weights.json`'s `_SPECIES_WEIGHTS`
— not a per-call sampler): (1) `usage_data/usage_stats.json`'s per-
species "Common Teammates" rank list (~230 species covered, reuses
`belief/determinize.py::_bring_subset_weights`'s existing `1/(rank+1)`
pattern, generalized to a full table); (2) `usage_data/team_cores.json`
(NEW scrape, `belief/usage_data/fetch_team_cores.py` +
`parse_team_cores.py`) — Pikalytics' `/ai/pokedex/championstournaments`
category-root page has a "Common Team Cores" section, top-5 ranked
2/3/4-Pokemon combos with real tournament team counts/%, only 15 entries
total (narrow but high-confidence, layered as a bonus on top of the
broader rank-decay signal, not a replacement).

**Mechanism is additive-per-pair, not whole-subset match/no-match**:
`pairwise_synergy_sum` sums `SYNERGY_WEIGHTS[a][b]` over all 6 pairs in a
candidate bring-4. A team that keeps one real known-good pair but pairs
it with two unrelated mons still gets that pair's full contribution, not
zero (partial credit, not a gate) — and a team with zero scraped-data
overlap anywhere just gets 0.0 synergy contribution, falling back to
pure type-coverage exactly like before this feature existed (no penalty
for being unrecognized; bonus-only signal, same as `mega_penalty` below).

**`mega_penalty`**: a flat, additive, boolean-gated subtraction (any
mega-eligible species in the bring-4 vs. none — never scaled by count,
since only one mon can ever actually mega per game) applied to bring-
subset scoring ONLY, never lead-pair scoring (a mega-less 2-mon lead is
normal, often-correct doubles play — protect the mega, bring it in later
on a good matchup; penalizing it there would incentivize front-loading
the mega into every lead). Deliberately soft, never a hard filter, and
deliberately NOT paired with hand-coded exception logic (e.g. detecting
"hard Trick Room + all owned megas are fast-and-frail") — a strong
type-coverage/synergy score on a genuinely-correct no-mega line already
overcomes a modest flat penalty on its own; simpler and more robust than
encoding exactly when the exception applies. Mega eligibility is
`reference/mega_stones.json` species membership (public, static), never
`mon.item` (hidden per-world attribute) — kept independent of the
synergy-weights threading entirely, no belief/ dependency needed for it.

**Dependency direction preserved**: `model/team_preview_scoring.py`
takes `synergy_weights`/`mega_penalty` as plain optional parameters
(default `None`/`0.0` — exactly inert, verified by the existing
pre-synergy regression tests passing unmodified with zero new kwargs),
`model/` never imports `belief/`. `harness/solver_player.py` and
`harness/heuristic_player.py` load `SYNERGY_WEIGHTS` once and thread it
(plus a real `mega_penalty=1.0` default) down through
`solve_team_preview_decision_parallel`/`TeamPreviewGame`/
`propose_pruned_team_preview_actions` and `choose_team_preview` alike —
same injection pattern already used for `sample_determinization`/
`sample_team_preview_world`.

**Small cleanup that rode along**: mega-forme→base-species-id folding
was duplicated in `belief/determinize.py` and
`belief/usage_data/build_weights.py`; hoisted into
`belief/species_folding.py` (also absorbing `parse_pikalytics.py`'s
`_to_id`) before a third near-identical copy would have been needed here.

### 2.10 Two more forced-switch stuck-loop bugs (found live, same day as §2.8)

Both in `model/heuristic.py`, both causing Showdown to re-issue an
identical mid-turn request hundreds of times (harmless to game correctness
— the request eventually got resolved some other way — but wasted real
wall-clock time and produced enormous, useless log files):

1. **Self-switching moves** (Parting Shot/U-turn/Volt Switch/Baton Pass/
   Flip Turn): `_choose_slot_action` only treated a slot as needing a
   switch when its mon was `None` or `fainted`. A mon forced out by its
   *own move's* effect is neither — it's alive with every move showing
   `disabled` (correctly; Showdown doesn't re-offer moves during a
   switch-only request), so the function fell through to `NoAction()`,
   which never satisfies a mandatory-switch request. Fixed: when a mon
   has no usable move at all, isn't trapped, and has a living bench mon,
   switch — that combination only arises from a pending forced switch or
   genuine Struggle-territory-with-a-bench, and switching is correct
   either way.
2. **`claimed_bench` leak between force-switch slots**: introduced by
   fix #1 itself. Both `harness/solver_player.py` and
   `harness/heuristic_player.py` used to compute both slots' actions via
   the general `choose_turn_actions(state)` and then override the non-
   participating slot to `NoAction()` afterward. But the non-
   participating slot's moves *also* read "disabled" (Showdown doesn't
   re-list them for a slot that isn't part of the current request), so
   fix #1's own fallback fired for it too — spuriously claiming the one
   remaining bench mon via the shared `claimed_bench` set before the
   slot that actually needed it got a turn, silently leaving the real
   request unanswered. Fixed: new `model/heuristic.py::
   choose_forced_switches(state, force_switch)` bypasses move-scoring
   entirely for this request type (it only ever offers a switch or a
   pass, never a move) — both harness players now call it directly
   instead of computing-then-discarding.

Regression tests: `model/test_heuristic.py` (both bugs, plus the
existing Struggle-territory/fainted-switch/normal-turn sanity cases,
confirmed still passing).

### 2.11 Self-switch moves: from a static heuristic to real search (2026-07-18)

**The bug**: a forced-lead diagnostic match (rain-lead solver vs sun-lead
solver, 1/5 win rate) showed Grimmsnarl's Parting Shot correctly
weakening the incoming threat, but always sending in Swampert over
Pelipper — not because search compared them, but because
`model/heuristic.py::choose_forced_switches` picks "first live bench
mon," and Swampert happened to come first in bench order. Pelipper is
clearly better here (Ground-immune to the opponent's Garchomp; its
Drizzle reverses the opponent's Sun to Rain on send-out, cutting a
pending Heat Wave's power) — exactly the kind of tactical payoff
Parting Shot/U-turn exist to create, which a type-blind heuristic
discards entirely.

**First design attempt, reverted**: a `ForcedSwitchGame` sibling of
`TeamPreviewGame`, resolving the switch as its own downstream search
node via an artificial `pending_switch` reconstruction in
`engine/bridge.js` (`Battle.makeRequest('switch')` + manually-set
`switchFlag`). Correctly handled the case where the opponent's action
had already resolved by switch-time, but a live-engine test proved it
structurally can't handle the case where the opponent HASN'T acted yet
(the reported bug's actual case, since Grimmsnarl's Prankster-boosted
Parting Shot goes before ordinary-priority moves): Showdown's own
request model never issues a second request to a side that already has
one — `getRequests('switch')` only generates a request for the side with
an actual `switchFlag` set, so the opponent's still-hidden move genuinely
has nowhere to attach in that reconstruction. Real Showdown represents
"opponent's still-pending move" as an already-queued action from the
turn's true start, not a fresh mid-pause request — the artificial
reconstruction never had that queue populated. Abandoned; see git
history (session of 2026-07-18) for the full design if a two-stage
pause/resume engine protocol is ever worth revisiting.

**Shipped design**: fold the switch-in choice into the SAME turn-
decision node that chooses the self-switch move, as an extra action
dimension — no new node, no new engine op, no tree-depth change.

- `MoveAction` gained `switch_bench_slot: Optional[int]`. In
  `model/action_space.py::propose_slot_actions`, any move with
  `reference/move_data.json`'s `selfSwitch` field set (Parting Shot,
  U-turn, Volt Switch, Baton Pass, Flip Turn, Shed Tail, Chilly
  Reception — sourced from the real vendored Dex, not guessed) branches
  over every living bench mon instead of emitting one `MoveAction`;
  `_pruned_slot_actions` exempts these branches from its normal best-
  per-move_slot dedup (which would otherwise arbitrarily collapse every
  bench candidate to one, since `_action_damage` can't distinguish
  them); `_joint` forbids two slots (a self-switch move and/or a plain
  voluntary switch) from targeting the same bench destination.
- The resolution mechanism needs ZERO engine changes: `Side.chooseSwitch()`
  with no slot given (Showdown's own default forced-switch auto-pick,
  used by `resolveForcedSwitches`/`autoChoose`) always takes the lowest-
  index living, not-yet-claimed bench mon in `side.pokemon` array order —
  confirmed by reading `vendor/pokemon-showdown/sim/side.ts` directly,
  not assumed. So controlling the destination is just a matter of which
  bench mon comes first in the team order handed to a fresh
  `init_battle` call. `model/solver_game.py::_resolve_self_switches`
  (called from both `EngineGame.step()` and `TeamPreviewGame.step()`'s
  post-team-preview branch): when `my`/`opp` includes a self-switch
  `MoveAction`, reorders that side's bench (`_reorder_bench`) and issues
  a fresh `bridge.init_battle()` before stepping; any OTHER plain
  `SwitchAction` on the same side that same turn gets its `bench_slot`
  translated through the same reorder (`_remap_switches`), so both
  choices stay mutually consistent. Falls through to the original
  handle/state untouched — zero extra engine calls — whenever nothing
  needs reordering (the common case).
- Move **failure** (Protect on the target; an immunity ability like
  Gholdengo's Good As Gold; the Gen 7+ rule that a Prankster-boosted
  status move fails against a Dark-type target; the opponent switching
  a hard-counter into that slot) needs no special-casing either: it's
  resolved by the real, unmodified engine exactly like any other move
  failure, and a failed move simply never sets `switchFlag` — confirmed
  live (Kingambit-under-Prankster and Gholdengo cases both tested
  directly against the engine: zero errors, no switch, target's boosts
  untouched). The opponent's action space already includes ordinary
  switches on both sides, so "opponent switches in a counter" is already
  one of the branches CFR naturally explores and weighs, with no new
  code.
- **Live play deliberately does NOT reuse the pre-decided
  `switch_bench_slot`.** By the time poke-env's real mid-turn
  `force_switch` request arrives, more has been revealed than was known
  at turn-submission time — critically, Mega Evolution always resolves
  before any move fires, even a Prankster-boosted one, so the opponent's
  mega status is always live-visible by switch-time even though their
  move might not be yet. `harness/solver_player.py` answers the live
  request via `choose_forced_switches` (unchanged call site) —
  `model/heuristic.py::_choose_switch_in` was upgraded from "first live
  bench mon" to a cheap (no engine call) damage-aware comparison: real
  `expected_damage` against any of the opponent's `revealed_moves`, or a
  generic type-effectiveness-based proxy (`_type_proxy_damage`) when
  nothing's revealed yet — evaluated fresh against the CURRENT battle
  state, so it picks up newly-revealed information for free rather than
  replaying a possibly-stale pre-turn decision.

Regression tests: `model/test_action_space.py` (self-switch branching,
empty-bench no-op, pruner exemption, joint-product collision filter),
`model/test_heuristic.py` (damage-aware switch-in, both the revealed-
move and type-proxy paths), `engine/test_self_switch_actions.py`
(destination control against the real engine, the opponent's still-
pending move actually firing against the switch-in, the remap-
correctness case, and the full-pipeline Swampert-over-Pelipper
regression: Parting-Shot-into-Pelipper converges to ~75% probability
mass vs ~7% for Swampert at 200 iterations).

### 2.12 Tier-1 smart pruning, and the depth-3 result that ended the tree track (2026-07-20)

`model/action_space.py::_filter_dominated_moves` (wired into
`_pruned_slot_actions`) cuts domain-obviously-bad branches before the
search ever spends a rollout on them:

- **Immune (0x) attacks** are always cut.
- **Resisted (<=0.5x vs every live target)** attacks are cut *only if* a
  neutral-or-better attack survives, so a mon whose every option is
  resisted still gets to act.
- **Prankster status into an all-Dark opposing side** is cut (the real
  mechanic: Prankster-boosted status can't touch Dark-types).
- **Support "attacks" are exempt** (`_SUPPORT_ATTACK_MOVES`: Icy Wind,
  Electroweb, Snarl, Bulldoze, Fake Out, ...) — their value is the stat
  drop / flinch, not the damage, so resistance is irrelevant.
- A fallback always keeps the best move if everything got cut.

**Keying-contract safety:** every cut is computed from PUBLIC info only
(my own mon, the opponent's revealed species/types, world-invariant
species estimates) — never the sampled hidden attributes — so my action
set stays identical across determinized worlds, which §2.1's contract
requires. Opponent-side cuts may use the sampled world (keyed per-world).

**Measured effect:** depth 3 at cap 3 became affordable (~65s vs ~31s
baseline for the same iteration budget; ~235s at cap 6), no OOM. Cheap
tactical wins showed up immediately — at low cap it swaps a dead move
for a real one (e.g. Incineroar drops Darkest Lariat into a Fairy and
keeps Parting Shot).

**But the depth-3 experiment is what killed the tree as the primary
direction.** Re-running the Trick Room team (MB501) vs Tailwind (MB496)
at depth 3: TR got *set up* 3/5 games (vs 0/5 at depth 2) — the deeper
search really did find the line — yet **conversion stayed 0/5**. Depth
bought the setup and not the win. Combined with a separate probe showing
single-turn tactics were already sound (Aerodactyl clicks Wide Guard
46.7% of the time into a Rock Slide threat, the correct read), the
conclusion was that the gap is **holistic policy quality, not lookahead
depth** — VGC is mostly rich current-turn judgement. That is the direct
motivation for §6.

## 3. CFR facts encoded in model/regret.py (don't relearn these)

- The strategy that converges is the TIME-AVERAGED one
  (`average_strategy()`), not the current iterate (which oscillates).
- Regret matching: play proportional to positive cumulative regret;
  uniform when none positive.
- Convergence certified by exploitability gap (sum of both sides'
  best-response values vs the average strategies -> 0), which doesn't
  require knowing the equilibrium in closed form.

## 4. Checklist

### Done
- [x] `schema/battle_state.py` — BattleState/actions contract
      (WeightedOption marginals, mega/tera fields, TurnActions).
- [x] Reg M-B legality data extracted from vendored Showdown source:
      314 species, 508 moves, 316 abilities, 148 items; per-species
      learnsets+abilities (`reference/species_data.json`), base stats
      (`species_stats.json`), move data (`move_data.json`), type chart
      (`type_chart.json`) — all user-validated.
- [x] `harness/` — bidirectional poke-env translation validated at scale
      (0 protocol errors after fixing the 6 request-protocol bugs; see
      memory: poke-env-request-protocol-gotchas).
- [x] `belief/tracker.py` — belief plumbing with placeholder uniform
      prior (interface-stable for later usage-mined priors).
- [x] `model/heuristic.py` + `damage_calc.py` — greedy baseline policy
      (loop-prover + first sparring opponent), plus readable battle
      logging (`model/battle_log.py`, `harness/heuristic_player.py`,
      `harness/run_heuristic_games.py`).
- [x] `model/regret.py` — regret-matching core + full-expectation matrix
      solver + exploitability. Tests pass (`python -m model.test_regret`):
      RPS -> uniform, dominance -> pure, asymmetric mixed game -> known
      equilibrium, exploitability gaps ~0.
- [x] Verified engine supports in-process arbitrary-state simulation
      (test/common.js pattern) — unblocks step().
- [x] `model/mccfr.py` — ExternalSamplingSolver: game-agnostic
      external-sampling MCCFR (multi-world root chance sampling,
      simultaneous-move levels, asymmetric keying, depth limit, injected
      leaf/step). Tests pass (`python -m model.test_mccfr`): noisy RPS
      -> uniform; anti-fusion decision problem (solver 1.5 vs naive
      fused 1.0); Bayesian matrix game -> equilibrium (guarantees 0.249
      vs naive 0.125, optimum 0.25); two-round pennies uniform at every
      node; depth-cutoff leaf steering.

- [x] `model/full_info_state.py` — FullInfoState (both sides as
      OwnPokemon; POV convention: each team's Position labels are that
      side's own slot a/b, Target.OPP_LEFT = other side's LEFT) +
      active/bench helpers + hp_leaf_value. `model/action_space.py` —
      propose_slot_actions/propose_turn_actions (the pruning seam):
      target branching per Showdown's move target field, mega
      True/False doubling for the stone holder (via new
      `reference/mega_stones.json`, 75 legal stones extracted from
      items.ts's modern `megaStone: {Base: Forme}` map format),
      switches, cross-slot filters (same-bench double switch, double
      mega). V1 exclusions documented in the module docstring (no
      deliberate ally-targeting of attacks, no trapping, no move-locks
      beyond `disabled`). Tests: `python -m model.test_action_space`.

- [x] `belief/determinize.py` — placeholder `sample_determinization()`:
      structurally correct (bring-subset hypothesis from unseen roster
      species + full hidden-attribute fill, jointly per call), uniform
      probabilities, but hard constraints enforced: revealed facts
      preserved exactly, learnset-legal moves, item clause, stones only
      on species they mega (none once the side's Mega is spent), an
      already-mega'd mon holds exactly its own stone. Stats = champions
      zero-investment floor until spread archetypes exist. Tests:
      `python -m belief.test_determinize`. Two structural changes rode
      along: (1) FullInfoState moved to `schema/full_info_state.py` (it
      is a 3-package contract: belief produces, model consumes, engine
      steps — belief/ must not import model/), leaf value split into
      `model/leaf_value.py`; (2) BattleState gained `opp_roster` (the
      opponent's full 6 preview species — public info the old schema
      dropped once preview ended), populated by the translator from
      poke-env's persistent teampreview_opponent_team.

- [x] `engine/` Node bridge (`bridge.js` + `bridge.py`): Sim.Battle
      in-process via a JSON-lines child, implementing init/step/free.
      Snapshot model: immutable serialized battles (Battle.toJSON), each
      step = restore parent + RESEED RNG (fresh chance per sample) +
      one turn + auto-resolve forced replacements (engine default choice
      = first switch-in) + store child. Root init reconstructs from
      FullInfoState: champions points recovered exactly from final stats
      (linear inverse, neutral nature — verified: engine recomputes
      identical stats for all mons), hp/status/boosts/pp/faints/turn/
      field/side conditions applied, elapsed->remaining duration
      conversion, one-mega-per-side via canMegaEvo=false. Known V1
      fidelity gaps (documented in bridge.js): root volatiles dropped,
      duration items assumed absent, sleep counter defaults. Exported
      states carry REMAINING durations in *_turns (engine semantics; only
      my_key/leaf/debug consume them — never re-init'ed). 19 checks pass
      (`python -m engine.test_bridge`): stat inversion, mutations echo,
      real turn damage, snapshot immutability, mega via choice flag,
      forced-replacement auto-resolution, play-to-terminal +1.
- [x] `harness/solver_player.py` + `harness/run_solver_match.py`: the
      integration milestone. `EngineGame`/`solve_decision`
      (`model/solver_game.py`) adapt enumerator+determinizer+bridge into
      `ExternalSamplingSolver`'s game protocol, with a pruned action
      proposer (`propose_pruned_turn_actions`, damage-greedy top-1-
      per-move-slot + best mega + one switch, the policy net's future
      seam) since raw ~96-action joints are too slow for engine-backed
      rollouts. First full 5-game match completed cleanly: solver 3/5 vs
      heuristic; after fixing bug #4 below (which was causing stalled
      retries, not just bad play) a second batch went 4/5, noticeably
      faster too (16-24s/game vs 18-77s) — promising but still n=5, not
      yet a statistically solid "beats it clearly" (next step: a larger/
      tuned validation batch). Today's settings are speed-tuned, not
      strength-tuned, and there's ~10x compute headroom left in the
      60s/turn budget (see the real-time budget discussion above this
      checklist). Five real bugs found via live matches and fixed, each
      with a permanent regression test
      (bridge suite now 9 cases, `python -m engine.test_bridge`; keying
      unit tests in `python -m model.test_solver_game`):
      1. `mega_used` was inferred from `canMegaEvo` (does any CURRENT mon
         hold a legal stone), which varies by determinization world (a
         hidden bench mon's sampled item differs per world) even before
         any mega has actually happened — leaked hidden info into what
         must be a world-independent key. Fixed: explicit `side.
         initialMegaUsed` flag set at init from the input FullInfoState,
         combined with `species.isMega` (permanent once a real mega
         happens) — never inferred from stone-holding.
      2. `_ordered_team`'s team-preview lead ordering silently flipped a
         living mon's LEFT/RIGHT label when the OTHER active slot was
         permanently empty (fainted, no living replacement — drops its
         position, so nothing was left to occupy team-order slot 0),
         sliding the survivor into the wrong slot. Fixed: reserve slots
         0/1 for LEFT/RIGHT specifically, padding with any fainted filler
         (order among the dead doesn't matter — re-killed immediately by
         applyMonState right after) rather than "whoever has a position
         first."
      3. Some held items/abilities (found: Metronome the item) attach a
         persistent engine-internal bookkeeping volatile the instant
         they're equipped — not something a real opponent could actually
         observe, but included in `_mon_public`'s "public" key since it
         reads straight from the engine echo. Since the item causing it
         is exactly the kind of hidden fact that varies per
         determinization world, this re-leaked hidden info into my_key.
         Fixed: opponent volatiles dropped from the public-key
         contribution entirely (known precision loss, not a soundness
         issue — the simulated state still has real volatiles, only the
         regret-table bucketing key is coarsened); kept for the
         opponent's own per-world key (`opp_key`), which is safe since
         it's already prefixed by world_id.
      4. Found via direct log inspection, not a crash: `harness/
         translator.py`'s `own_pokemon()` never populated `MoveSlot.
         disabled` at all — defaulted `False` unconditionally, so a
         genuinely unusable move (Fake Out after turn 1, Torment/Taunt/
         Disable/choice-lock) always looked pickable. The solver (and
         latently the heuristic before it, unnoticed) could "choose" it,
         Showdown would reject the choice, and the harness would stall
         retrying the same turn indefinitely — exactly the repeating-
         turn pattern the user spotted in a sample log. Fixed:
         `battle.available_moves[i]` (poke-env's own request-parsed
         "currently legal" list, already filtering Showdown's `disabled`
         flag) is now threaded through for active mons. Regression
         coverage: live-battle `harness/test_translator.py` rerun clean,
         plus a dedicated fast no-server unit test
         (`harness/test_translator_unit.py`).
      5. Found scaling to a bigger validation batch (n_worlds=3): a
         side-effect of RECONSTRUCTING the battle, not of anything about
         the true game state, could itself leak hidden info. My own
         Incineroar's Intimidate legitimately fires again every time its
         send-out is replayed during `init_battle` — and `applyMonState`
         only *set* boosts/status when the schema value was truthy,
         silently skipping whenever the true observed value was a
         genuine 0/none. So whatever the engine's own fresh computation
         produced (itself dependent on the OPPONENT's hidden, per-world-
         sampled item — e.g. Clear Amulet blocking the drop, White Herb
         undoing it) leaked through as if it were the real public fact,
         instead of the true observed value overriding it. Same bug
         class as #1 (mega_used), different mechanism. Fixed: boost
         assignment is now unconditional (always overwrite, including
         with 0) and status gained an `else` branch that explicitly
         clears it when the true state says none — "authoritative
         source always wins" applied consistently rather than
         conditionally.
- [x] Forced-continuation + trapping support (depth-2+ search correctness
      fix): `propose_slot_actions` and the enumerator only ever checked
      `pp`/`disabled` on a mon's normal 4-move list - it had no notion of
      "this mon's whole action space is one forced move" (mid-recharge,
      mid-two-turn-move like Solar Beam/Fly) or "cannot switch right now"
      (trapping abilities/moves). Both only manifest the turn AFTER their
      trigger, so depth-1 search never hit them; at depth 2 they caused
      25-56% of all rollouts to error (1601/5786 and 809/1435 in the
      diagnostic that found this). Fixed at the source: `OwnPokemon`
      gained a `trapped: bool` field; `engine/bridge.js`'s `exportMon`
      now calls `Pokemon.getMoveRequestData()` - the SAME call Showdown's
      own request generation uses, not a reimplementation - which
      correctly narrows `moves` to one synthetic/real entry when locked
      and reports `trapped` (unified: a locked mon is always also
      reported trapped, confirmed against source). `propose_slot_actions`
      now: skips switches entirely when `trapped`; when `trapped` AND
      `moves` has exactly one entry, returns exactly that one MoveAction
      with move_slot=1 and no target (verified against source: the
      target, if any, was already locked in on the original turn - a
      locked-branch request entry carries no target field at all).
      `harness/translator.py` also threads poke-env's `battle.trapped[i]`
      into the live path for consistency. Keying
      (`model/solver_game.py`): `trapped` added to the public key (unlike
      opponent volatiles, it directly changes the action-set size, so the
      keying contract requires it) - one accepted subtlety documented
      inline: if trapped depends on an opponent's still-unrevealed
      ability, it can legitimately differ across determinization worlds;
      this isn't a bug like mega_used/boosts were, it mirrors Showdown's
      own trapped/maybeTrapped distinction (a real player wouldn't know
      either). Verified against the real engine: Solar Beam charge->
      release (moves narrow to 1, trapped flips, real damage confirmed on
      release) and Hyper Beam recharge (same, modulo its 90% accuracy -
      confirmed the self-effect only applies on a hit, matching real
      mechanics, not a bug). Depth-2 diagnostic re-run after the fix:
      error counts went from 1601/5786 and 809/1435 to 0/5410 and
      0/1215. Bridge suite: 10 cases now (`python -m engine.test_bridge`).
      **Ability-based trapping (Shadow Tag - the only champions-legal
      trapper; Arena Trap itself isn't champions-legal) — found and
      fixed, not deferred.** Root cause was NOT what it first looked
      like: the ability/event system (`runEvent('TrapPokemon', ...)`,
      Shadow Tag's `onFoeTrapPokemon` hook, `tryTrap()`) works correctly
      even for a mon constructed starting AS its mega forme - confirmed
      directly with a standalone Node diagnostic against the real engine,
      which ruled out the mega-construction hypothesis entirely. The
      actual bug: `Pokemon.getMoveRequestData()` deliberately HIDES
      trapped-status in its exported `data.trapped` field when the cause
      is an undiscovered ability - `tryTrap(true)` sets `p.trapped` to
      the string `'hidden'` (not `true`), and the export logic uses a
      strict `=== true` check that excludes it, so a real player who
      hasn't found the trapping ability yet correctly isn't told. Right
      for the live protocol (poke-env's `battle.trapped` mirrors this
      correctly); wrong for search, which reasons inside an already
      fully-determinized world with no information left to hide from
      itself. Fixed in `exportMoves()`: read `p.trapped` directly
      (truthy check covers both `true` and `'hidden'`) instead of the
      protocol-gated `req.trapped`. Verified against the real engine:
      Shadow Tag traps both my active mons (doubles-wide passive effect,
      confirmed empirically), and - without any special-casing on our
      side - a Ghost-type mon (Gholdengo) is correctly immune, because
      `tryTrap()` gates through the engine's own `runStatusImmunity('trapped')`
      -> `dex.getImmunity('trapped', pokemon)` type-immunity check before
      ever setting `p.trapped`, entirely upstream of our fix. Bridge
      suite: 11 cases, 33 checks (`python -m engine.test_bridge`).
      **A sixth bug surfaced going from n_worlds=2 to n_worlds=3**
      (5% of rollouts erroring at depth 1, previously 0): Curse is the
      one move in the whole dex whose effective target depends on the
      USER's own type, not a fixed per-move property (confirmed in
      data/moves.ts: Ghost-type users target an opponent; every other
      user self-buffs atk/def at the cost of speed, with no target at
      all). `reference/move_data.json`'s static lookup only captures the
      Ghost-type default ("normal"), so a non-Ghost Curse-user got
      offered opponent targets that the engine correctly rejected.
      Fixed with a one-off special case in `propose_slot_actions`
      (mirrors how the real engine itself hardcodes this exact
      exception rather than generalizing a "type-dependent target"
      mechanism for a single move). Depth-1 and depth-2 both confirmed
      at 0 errors after the fix (`model/test_action_space.py` covers
      both the Ghost and non-Ghost cases).
- [x] **Parallel engine workers** (`engine/pool.py` + `model/solver_game.py`'s
      `solve_decision_parallel`): the actual speedup lever, in response to
      depth-2 batch validation being impractically slow otherwise (10
      games at depth 2 taking ~14 minutes sequentially, and the user's
      real goal — many games against a pool of meta teams — needing this
      to not take all day). Design: split `iterations` across N
      independent `EngineBridge` workers, each running its OWN local
      `EngineGame`/`ExternalSamplingSolver` from the SAME `root_states`
      (identical content -> identical my_key/opp_key regardless of which
      worker computed them, so results are directly comparable), then sum
      the resulting regret tables (`_merge_regret_tables`) — standard
      practice in large-scale CFR solvers (independent partial solves
      from a shared root, merged), not a novel shortcut. Needs ZERO
      changes to `engine/bridge.js` or the core MCCFR algorithm in
      `model/mccfr.py` beyond one small addition: `ExternalSamplingSolver.
      run()` gained a `traverser_offset` parameter so workers can stagger
      which side starts as traverser (each worker's local iteration
      counter restarts at 0, so without staggering every worker would
      open with the same side and skew the merged ME/OPP balance).
      `EngineBridgePool` starts its N worker subprocesses concurrently via
      a thread pool (each `EngineBridge.__init__` does a blocking `ping`;
      sequential startup would make pool cost scale with worker count).
      Validated in two stages, per the established practice of proving
      algorithm correctness on a toy game before the real engine:
      1. `model/test_solver_parallel.py` — `_merge_regret_tables` unit
         tests (sums matching keys, includes solo keys as-is, raises on
         an action-count mismatch) plus a toy matrix-world game with a
         known equilibrium: splitting the same total iteration count
         across 6 independent workers and merging converges to the same
         answer as one sequential solve (no engine needed, fast).
      2. `engine/test_pool_speedup.py` — real engine, depth 2,
         iterations=16: single bridge took 40.0s (10,731 rollouts, 0
         errors); pool of 8 took 10.4s (10,586 rollouts, 0 errors) —
         **3.8x speedup**, with pool startup itself only 0.2s (confirms
         it's cheap enough to create once per match and reuse for every
         decision, not per-decision). The shortfall from a theoretical
         8x is expected, not a bug: each round trip's JSON parsing and
         Pydantic model construction is CPU-bound Python work that holds
         the GIL even inside a thread, so it doesn't parallelize as
         cleanly as the pure I/O wait portion does.
      Wired into `harness/solver_player.py` (now holds a persistent
      `EngineBridgePool`, `n_workers=8` default) and
      `harness/run_solver_match.py`. Not yet explored: whether more than
      8 workers helps further, or whether switching from threads to
      separate OS processes would raise the ceiling by sidestepping GIL
      contention on the CPU-bound portion of each round trip.
- [ ] **Commit checkpoint**: once the solver demonstrably beats the
      heuristic baseline at a statistically solid sample size (currently
      4/5 in the latest small batch — promising, not yet conclusive;
      next step is a larger/tuned validation batch), commit (user: "once
      the model is ready to be trained"). Battle-log explainability
      (root strategy + beliefs shown per turn) would help judge quality
      too.
- [x] **Search-based team preview** (§2.8): replaced the placeholder
      bring/lead heuristic (used by both players, never searched) with a
      real `TeamPreviewGame` (`model/solver_game.py`, sibling of
      `EngineGame`) composed onto the existing MCCFR/regret machinery
      with zero changes to either — depth_limit=2, team preview resolves
      through a genuinely fresh engine battle at depth 1 (new
      `engine/bridge.js` op `init_team_preview`; team-preview *submission*
      needed no new op, Showdown's own `side.choose()` already dispatches
      it through the existing `step` RPC), a real turn-1 exchange resolves
      at depth 2. New determinizer (`belief/determinize.py::
      sample_team_preview_world`, reuses `_fresh()` unchanged) and pruner
      (`model/action_space.py::propose_pruned_team_preview_actions`,
      species-only type-coverage scoring, world-invariance regression-
      tested). Measured cost at realistic settings: 4,950-7,260 rollouts
      in 5.6-6.1s on an 8-worker pool — well under the existing ~30-45s
      in-battle decision ballpark. Live-validated: the deterministic
      every-game bad-lead bug that motivated this (§2.8's own example -
      found via a non-mirror-match test batch) is confirmed gone; bring/
      lead now varies game to game. Wired into `harness/solver_player.py`
      as the new default (`use_search_team_preview=True`); the old
      heuristic remains available as an opt-out fallback.
- [x] **Team-synergy + mega-usage scoring** (§2.9): both team-preview
      scoring consumers (`model/action_space.py`'s pruner and
      `model/heuristic.py::choose_team_preview`, now genuinely opponent-
      aware) share `model/team_preview_scoring.py`, blending real
      Pikalytics teammate/team-core data (`belief/team_synergy.py::
      SYNERGY_WEIGHTS`, additive per-pair, never a whole-subset gate) and
      a soft flat `mega_penalty` for zero-mega bring-4 subsets. New scrape
      (`belief/usage_data/fetch_team_cores.py`/`parse_team_cores.py` →
      `team_cores.json`, 15 real 2/3/4-Pokemon cores). Species-folding
      duplication hoisted to `belief/species_folding.py` along the way.
      Regression-tested at every layer (primitives, world-invariance
      extended, a synergy-driven bug-regression mirroring the type-
      coverage one, mega soft-vs-hard, `TeamPreviewGame` plumbing, and
      `SYNERGY_WEIGHTS` itself) — `model/test_team_preview_scoring.py`,
      `model/test_team_preview_actions.py`, `model/test_team_preview_
      game.py`, `belief/test_team_synergy.py`. Two more forced-switch
      stuck-loop bugs found and fixed the same day, unrelated to this
      feature but in the same file — see §2.10.
- [ ] Value net replacing HP-diff leaf (self-play training loop);
      policy net for action pruning (propose_actions seam).
- [ ] Meta layer v2: usage/replay-mined priors + learned correlations
      (move co-occurrence beyond team cores).
- [ ] Later/parked: two-sided ranges (opponent's uncertainty about us);
      forced-replacement decision nodes inside search; chance-outcome-
      aware node keying; Tera support when Champions ships it.

## 5. Open questions (not yet decided)

- K (determinizations per decision) and iteration budget per real turn —
  tune empirically once the loop runs.
- Exact serialization of the public observation snapshot used as my node
  key (what to include/round so keys are stable and tables don't blow
  up). The action-set-consistency half is now enforced by the solver's
  keying contract (section 2.1); at the root my action set is fully
  public so the old "legal in some worlds only" concern dissolves.
- Reward shaping for value-net training: pure win/loss vs light HP
  shaping to bootstrap.

---

## 6. The replay-trained net (primary direction as of 2026-07-20)

**Thesis.** VGC is dominated by rich *current-turn* judgement, not deep
lookahead (§2.12's depth-3 result). So the real solver is a
policy+value network trained by imitation on real human replays, used
either directly (depth 0) or wrapped in a shallow search that uses the
policy to propose branches and the value head to score them (depth 1).
The MCCFR tree is retained as the reference opponent, and as the
policy-improvement operator a future self-play loop could use.

### 6.1 Replay pipeline (`replays/`)

Three stages, each independently tested:

- `scrape_replays.py` — Showdown's public, no-auth endpoints:
  `search.json?format=<fmt>&page=<n>` (51/page, carries rating) and
  `<id>.json` (metadata + full protocol log). Two formats:
  `gen9championsvgc2026regmb` (Bo1) and `...regmbbo3` (Bo3). Only Bo3
  carries `|showteam|` **open team sheets** (full item/ability/move/
  nature/EV ground truth for BOTH sides) — the gold data for the belief
  and team-preview work. Rating-filtered at the cheap metadata stage,
  resumable, polite. Raw cache is gitignored (reproducible download).
- `parse_replays.py` — protocol to structured record. Three gotchas that
  cost real time: the trailing `|player|p1|` reset line blanks the name
  (guard on non-empty), per-player rating is `parts[5]` not `parts[4]`
  (index 4 is the avatar, which can be numeric), and the `|showteam|`
  payload itself contains `|` (split with maxsplit=3).
- `reconstruct.py` — walks the log maintaining board state and emits one
  (state, action) example **per side per turn**, snapshotted BEFORE the
  turn resolves (the true decision state). Tracks HP fraction, status,
  boosts (cleared on switch-out), faints, revealed item/ability/moves,
  weather, Trick Room, terrain, side conditions.

**Corpus:** 4,834 Bo1 + 4,987 Bo3 = **9,821 replays**, 65,901 turns,
**122,180 examples**, 99.99% outcome-labeled, all 4,987 Bo3 with full
open sheets.

Known reconstruction gaps: exact residual-damage attribution; volatiles
beyond the tracked set; **Illusion** (Zoroark/Zorua share the copied
species' dict key, which a real mega re-key can orphan — rare, and
`encode_state` tolerates the resulting phantom active pointer).

### 6.2 Encoder (`model/encoding.py`)

Framework-neutral (numpy only), so vocab/feature logic is testable
without the training stack and `model/` stays independent of `replays/`
and poke-env.

Per-ENTITY tokens (the shape a transformer wants), at **fixed slot
positions** so a per-slot policy head always reads the same index even
when a slot is empty: me active a=0, b=1, bench 2-5; opp 6-11; plus a
field token. Per token: species/item/ability/status ids, up to 4 move
ids, a `numeric` battle-state vector (hp, is_me/active/fainted, 7
boosts), and a `static` vector.

**`static` is the role-generalization lever** (6 normalized base stats +
18-type multi-hot, from `reference/species_stats.json` and
`type_chart.json`). It is deliberately a SEPARATE tensor from `numeric`
so that training-time **species dropout** can null the species-identity
embedding while the role profile survives. That is what lets the net
transfer between same-role mons: Incineroar (95/115/90/80/90/60,
Fire/Dark, Intimidate, Fake Out) and Scrafty (65/90/115/45/115/58,
Dark/Fighting, Intimidate, Fake Out) look alike as *profiles* regardless
of name. Coverage verified: 331 distinct corpus species, **zero** with
missing stats or types; 0% UNK over 754,699 species tokens and 191,004
played moves.

**Meta layer as model input:** per token, the belief usage prior's most
likely item and ability (plus probabilities), so the net keys off "what
this species usually runs" before anything is revealed, and adapts when
the usage table is refreshed rather than needing a retrain.

### 6.3 Network + training (`model/policy_net.py`, `dataset.py`, `train.py`)

~728k params, deliberately small — the generalization lever is feature
design + species dropout + data diversity, not capacity (more capacity
mostly buys memorization, the opposite of the goal). 4-layer
TransformerEncoder, d_model 128, 8 heads, norm_first, key-padding-masked
so empty slots are excluded from attention. Policy heads are **shared**
and applied to both me-active tokens (the same policy function decides
for each active mon): action-type / move / target / mega / switch. The
value head reads a masked-mean pool.

Loss is rating-weighted and mask-gated: the type head trains only where
the slot actually acted, move/target/mega only on move slots, switch
only on switch slots, value on every example.

**v1 results** (43,376 examples at rating >= 1200, 39k/4.3k split, 25
epochs, ~5s/epoch on an RTX 3080 Ti):

| metric | init | final |
|---|---|---|
| move-acc (exact played move, 510-way) | 0.00 | **0.46** |
| type-acc (move vs switch) | 0.14 | 0.89 |
| value-acc (win prediction) | 0.53 | **0.58** (still rising) |

move-acc 0.46 against a ~0.25 random-within-legal baseline is a real
"learned to play" signal (validation runs with species dropout OFF).
Value was still climbing when training stopped and is the weak head.

### 6.4 Qualitative position eval (`model/eval_positions.py`)

Accuracy alone cannot tell you if play is *sensible*, so the net is run
on positions whose right answer we understand:

- **WIN** — slow Farigiraf into a fast side: **Trick Room 0.88**. Exactly
  the line the MCCFR tree kept failing to convert (§2.12).
- **SOFT** — Incineroar lead: Parting Shot 0.44, Flare Blitz 0.30,
  Fake Out 0.26. Defensible, but under-picks Fake Out.
- **MISS** — Aerodactyl + Charizard into Garchomp's Rock Slide: **Wide
  Guard only 0.06**. Charizard eats Rock Slide at 4x, so Wide Guard is
  strong; imitation underweights *rare, high-skill* reads. **This is the
  concrete argument for depth-1 search:** the value head, scoring the
  leaf where Charizard survives, can catch what the policy alone will
  not propose.

**Encoding gap found:** there is no "just switched in" / turn-number
signal, so Fake Out (and every other switch-in-conditional move) cannot
be valued correctly. Add before the next retrain.

### 6.5 Depth-1 policy+value search (`harness/net_search.py`)

Per turn: (1) net policy ranks my legal joint actions, keep top-k_my;
(2) per determinized world, the **side-flipped** netstate gives the
opponent's policy, keep top-k_opp (a policy-weighted opponent model, not
uniform and not worst-case); (3) the engine rolls each (my, opp) pair
one real turn forward — a terminal turn yields a true +/-1, otherwise the
value head scores the leaf; (4) my action's score is the mean over
worlds of the opp-policy-weighted leaf value; take the argmax.

It reuses the existing legal-action enumeration (so every candidate is
engine-ready) and the existing encoder action labels (so the net can
score them) — no new action logic. Live cost is ~48 rollouts/turn (3
worlds x 4x4) at **~0.16s**; a whole net-vs-heuristic game runs ~5s
against ~40s+ for solver games.

Supporting bridges: `harness/net_translate.py` (BattleState /
FullInfoState to the neutral netstate, plus `flip_netstate`) and
`model/net_infer.py` (batched value, policy, candidate scoring — kept
input-source-neutral so `model/` never imports poke-env or the schema).

### 6.6 Live player + measured results

`harness/net_player.py` (`NetPlayer`) mirrors `SolverPlayer`'s
translate, determinize, TurnActions, poke-env order pipeline, swapping
the CFR solve for the depth-1 net search. It uses the SAME search-based
team preview as `SolverPlayer` (so comparisons are not decided by team
building); the learned team-preview head is future work.

- **vs HeuristicPlayer:** net+Aero 2/2, net+Swampert 0/2. Pure team
  strength — the same confound as §2.8's non-mirror lesson.
- **vs SolverPlayer, mirror team MB552, 10 games:** **net 3/10 (30%)**.
  Both sides identical roster AND identical team preview, so the
  per-turn engine was the only variable. **Not conclusive** (n=10, so a
  95% CI of roughly 7-65%), and contaminated (§6.7/§6.8). Honest read:
  the net is *not yet better* than the tuned CFR solver.

**Mirror matches are a poor skill gauge** and should not be repeated as
the primary test: identical teams mean identical speed, so every speed
tie inside the rollouts is a coin flip and leaf values are half noise.
MB552 additionally has near-universal OHKOs (Iron Head OHKOs Sylveon,
Rock Slide OHKOs Charizard, the Garchomps OHKO each other, Heat Wave
brings Kingambit to sash). Evaluate on DIVERSE teams with n >= 30.

### 6.7 Behavioral diagnostics — the most actionable findings

Over the 10 mirror games (75 net move-clicks):

- **The net NEVER protects and NEVER voluntarily switches** — 0 Protect/
  Detect, 0 voluntary switches. (Beware when reading logs: most "switch"
  lines are forced post-faint replacements, or the `[opponent]` logger.)
  Humans at rating >= 1200: protect-family **13.3% of moves** (Protect is
  the single most common move at 12.4%) and **10.2%** voluntary switches.
- **The cause is compound.** On validation, the policy assigns **12.2%**
  average mass to protect-family — nearly the 13.3% human base rate — but
  recall when a human actually protected is only **16.4%** versus
  **49.9%** on everything else. It has learned the BASE RATE, not the
  CONTEXT. Then depth-1 with a near-chance value head cannot price a
  next-turn payoff, so what survives gets demoted.
- **Crucially, the SOLVER also clicked Protect 0/66 times.** This is a
  shared search-horizon/evaluator failure, NOT a net-specific imitation
  flaw — blame the evaluator and the horizon before the training data.
- **A clear imitation WIN:** Kingambit's Sucker Punch share was **78%
  (14/18) for the net versus 33% (3/9) for the solver**. The net learned
  a genuinely contextual heuristic — slow mon, both opponents faster and
  threatening a KO, so take the priority damage — that the hand-built
  tree does not weight.
- **The net search lacks the tree's Tier-1 pruning:** it draws candidates
  from raw `propose_slot_actions`, while the solver uses
  `propose_pruned_turn_actions`. That is why Charizard clicked Heat Wave
  into Garchomp + Charizard (both resist).

### 6.8 Bugs found live (all engine/harness, none reproducible offline)

1. **Engine handle leak** — `net_search` called `init_battle` per rollout
   and never freed. Node died with *"Reached heap limit - JavaScript
   heap out of memory"*, and GC-thrashed long before that, which looks
   exactly like a hang. Fix: `init_battle` ONCE per world, `step()`
   branches from the same `(handle, root)` (the same primitive
   `EngineGame` uses), all handles tracked and freed in a `finally`.
   Also made decisions ~5x faster (0.8s to 0.16s). Soak-guarded in
   `harness/test_net_search.py` (25 decisions on one bridge).
2. **Forced-continuation stall** — after Hyper Beam, Showdown replaces
   the request's move list with ONE synthetic id (`recharge`) that is not
   in the mon's moveset, so every real move read "disabled", the policy
   emitted `NoAction`, and the server answered *"[Invalid choice] Can't
   pass: Your Sylveon must make a move"*, producing a retry loop (games
   of 155-374s versus a true ~40s). **A first fix was wrong and is worth
   remembering:** narrowing `OwnPokemon.moves` to the synthetic id broke
   the SOLVER, because those objects feed `init_battle` to `buildSet`
   and a synthetic id has no PP data (`FullInfoState` ValidationError on
   pp/max_pp being None). **Correct fix:** the translator keeps the real,
   engine-BUILDABLE moveset, and the forced continuation is resolved at
   the ORDER boundary (`harness/actions.py::_forced_move`), where the
   live request is still in hand. Struggle is deliberately NOT
   switch-overridden (switching out of Struggle is legal; recharge sets
   `trapped: true`). Tests: `harness/test_forced_move.py`.
3. **In-search recharge blindness (OPEN)** — the same recharge case still
   breaks *inside* the search: the world rebuilt by `init_battle` does
   not know the mon must recharge, so the proposed pass is rejected and
   logs show `48 rollouts, 48 engine rejections` — the search gets ZERO
   signal and picks blind, in at least 3 of 10 games. Must be fixed
   before any rerun is trustworthy.

### 6.9 Planned improvements (priority order)

1. **Fix in-search recharge blindness** — thread the must-recharge state
   into the reconstructed world so rollouts are legal. Prerequisite for
   any meaningful net-vs-solver number.
2. **Tier-1 pruning in the net search** — reuse
   `propose_pruned_turn_actions`; kills the resisted-attack class
   (Heat Wave into a double resist) immediately.
3. **Mixed strategy instead of argmax.** The depth-1 search already
   builds a payoff MATRIX (my k by opp k, to leaf value); solve that
   small zero-sum matrix for an equilibrium (LP, or regret matching in
   microseconds) rather than taking the max. This does triple duty:
   (a) it largely restores Protect/switch behaviour *for free* — sampling
   a policy that already puts ~12% on Protect plays it ~12% of the time
   instead of 0%; (b) a pure strategy is exploitable in a
   SIMULTANEOUS-MOVE game, and this is the correct fix; (c) it is the
   prerequisite for sound self-play (pure-strategy improvement can cycle,
   with rock-paper-scissors dynamics). It also yields exactly the desired
   context-dependence with no hand-tuning: where an action dominates, the
   equilibrium IS pure; where the spot is volatile, it is mixed.
4. **Value-head convergence** — the real bottleneck. Depth-1 is only as
   good as its evaluator, and 0.58 is near chance. More epochs, a higher
   value-loss weight, and ideally self-play outcome labels (cleaner than
   imitation's noisy "this player happened to win eventually").
5. **Encoder v3** — add a per-mon "entered this turn" flag (plus a turn
   counter) so switch-in-conditional moves (Fake Out) can be valued, and
   a must-recharge/locked flag so the net can see forced continuations.
6. **Learned team-preview head** — same token architecture over both full
   rosters with no board state, trained on replay turn-1 leads. Bo3 open
   sheets give the opponent's full team, so it can learn matchup-
   conditioned leads ("lead Incineroar + Farigiraf generally, but into a
   Mega Floette — or an opponent with no Fake Out of their own — prefer
   Incineroar + Slowking") instead of the hand-tuned core/type balance.
7. **Re-evaluate properly** — diverse teams from the 555-team pool,
   n >= 30, never a mirror.
8. **Self-play RL fine-tuning** (the longer arc) — the pieces exist:
   policy+value net, a real simulator with true terminals, a search that
   improves on the raw policy, and the encoder/training loop. Fine-tuning
   from the imitation net skips the expensive tabula-rasa phase. Requires
   (3) first for a sound target; imperfect information stays approximate
   via determinization (ReBeL-style belief-conditioned value is the
   rigorous version if it becomes necessary).
