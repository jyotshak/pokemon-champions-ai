"""External-sampling MCCFR over simultaneous-move, multi-world games.

Game-agnostic: the solver only sees an injected game object (documented
protocol below) — the Pokemon-specific pieces (action enumeration, the
Showdown engine bridge's step(), determinization sampling) plug into it
later without this file changing.

Structure it encodes (see docs/solver_design.md sections 2.1-2.3):

- Multi-world hidden information: each iteration samples one world (a
  determinization of the opponent's hidden state) proportional to its
  probability, then traverses within it. MY infoset keys are
  world-independent by contract, so my regret tables are shared across
  worlds — every world's counterfactual values accumulate into the same
  nodes, which is what prevents strategy fusion (acting differently in
  worlds I cannot distinguish). The OPPONENT knows their own set, so
  their keys include their private info and their tables are per-world.
- Simultaneous turns: one tree level = both sides commit, then step().
  Each side's strategy at a level is looked up before either action is
  chosen, so neither conditions on the other's same-turn choice.
- External sampling: the traverser enumerates all their actions (regret
  updates happen there); the other side's action is sampled from their
  current regret-matching strategy (and their average strategy is
  accumulated there); chance is sampled by just letting step() use its
  RNG. Traverser alternates each iteration. Convergence is in
  expectation over iterations — leaf noise is fine.
- Depth limit: after `depth_limit` turns, game.leaf_value() evaluates
  the frontier instead of recursing (terminal states short-circuit
  earlier with their exact value).

Game protocol (duck-typed):

    worlds() -> list[(initial_state, probability)]
        Probabilities must sum to 1. All initial states must share the
        same my_key (I cannot distinguish worlds at the root).
    is_terminal(state) -> float | None
        My-POV value in [-1, 1] if the game is over, else None.
    leaf_value(state) -> float
        My-POV heuristic value at the depth cutoff, same scale.
    my_actions(state) -> list          (labels; order defines indices)
    opp_actions(state) -> list
    step(state, my_action, opp_action, rng) -> next state
        May be stochastic (use the rng).
    my_key(state) -> hashable
        Must depend on PUBLIC information only — identical across worlds
        that are indistinguishable to me — and must fully determine
        my_actions(state). Violations raise at node lookup.
    opp_key(state) -> hashable
        Should include the opponent's private info (their world), since
        they legitimately condition on it.
"""

from __future__ import annotations

import random
from typing import Any, Hashable

from model.regret import RegretNode

ME = 0
OPP = 1


def _sample_index(strategy: list[float], rng: random.Random) -> int:
    r = rng.random()
    acc = 0.0
    for i, p in enumerate(strategy):
        acc += p
        if r <= acc:
            return i
    return len(strategy) - 1  # float-rounding fallthrough


class ExternalSamplingSolver:
    def __init__(self, game, depth_limit: int, rng: random.Random | None = None):
        self.game = game
        self.depth_limit = depth_limit
        self.rng = rng or random.Random()
        self.my_nodes: dict[Hashable, RegretNode] = {}
        self.opp_nodes: dict[Hashable, RegretNode] = {}
        self._worlds = game.worlds()
        root_keys = {game.my_key(state) for state, _ in self._worlds}
        if len(root_keys) != 1:
            raise ValueError(
                f"root my_key differs across worlds ({root_keys}) - worlds must be "
                "indistinguishable to me at the root"
            )
        self._root_key = root_keys.pop()

    def run(self, iterations: int, traverser_offset: int = 0) -> list[float]:
        """Run traversals (alternating traverser each iteration) and return
        the root average strategy over my root actions. `traverser_offset`
        shifts which side starts as traverser — for parallel solving
        (model/solver_game.py's solve_decision_parallel), each worker
        restarts its own local t=0, so without this every worker would
        open with the same side, skewing the merged ME/OPP iteration
        balance; staggering offsets across workers keeps it even.
        """
        for t in range(iterations):
            state = self._sample_world()
            self._traverse(state, depth=0, traverser=(t + traverser_offset) % 2)
        return self.root_strategy()

    def root_strategy(self) -> list[float]:
        return self.my_nodes[self._root_key].average_strategy()

    def root_actions(self) -> list[Any]:
        return self.game.my_actions(self._worlds[0][0])

    @property
    def root_key(self) -> Hashable:
        return self._root_key

    def _sample_world(self) -> Any:
        r = self.rng.random()
        acc = 0.0
        for state, prob in self._worlds:
            acc += prob
            if r <= acc:
                return state
        return self._worlds[-1][0]

    def _node(self, table: dict, key: Hashable, n_actions: int) -> RegretNode:
        node = table.get(key)
        if node is None:
            node = RegretNode(n_actions)
            table[key] = node
        elif node.n_actions != n_actions:
            raise ValueError(
                f"infoset key {key!r} seen with {node.n_actions} actions and now "
                f"{n_actions} - a key must fully determine its legal action set"
            )
        return node

    def _traverse(self, state: Any, depth: int, traverser: int) -> float:
        """One walk below `state`; returns a sampled estimate of the state's
        my-POV value under the current strategies.
        """
        game = self.game
        terminal = game.is_terminal(state)
        if terminal is not None:
            return terminal
        if depth >= self.depth_limit:
            return game.leaf_value(state)

        my_acts = game.my_actions(state)
        opp_acts = game.opp_actions(state)
        my_node = self._node(self.my_nodes, game.my_key(state), len(my_acts))
        opp_node = self._node(self.opp_nodes, game.opp_key(state), len(opp_acts))
        s_me = my_node.current_strategy()
        s_opp = opp_node.current_strategy()

        if traverser == ME:
            j = _sample_index(s_opp, self.rng)
            values = [
                self._traverse(game.step(state, a, opp_acts[j], self.rng), depth + 1, traverser)
                for a in my_acts
            ]
            node_value = sum(p * v for p, v in zip(s_me, values))
            my_node.update_regret(values, node_value)
            opp_node.accumulate_strategy(s_opp)
            return node_value

        i = _sample_index(s_me, self.rng)
        values = [
            self._traverse(game.step(state, my_acts[i], b, self.rng), depth + 1, traverser)
            for b in opp_acts
        ]
        opp_values = [-v for v in values]  # zero-sum: opponent regrets in their own POV
        opp_node_value = sum(p * v for p, v in zip(s_opp, opp_values))
        opp_node.update_regret(opp_values, opp_node_value)
        my_node.accumulate_strategy(s_me)
        return -opp_node_value
