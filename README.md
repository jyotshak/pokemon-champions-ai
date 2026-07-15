# Pokemon Champions Team Builder & Battle AI

A VGC-style (doubles) battle AI for Pokemon Champions: a logic layer that plays
a battle turn-by-turn (team preview selection, move/switch/tera/mega
decisions) reasoning under uncertainty about the opponent's hidden team
info, plus a computer-vision layer (planned) that reads Pokemon Champions
running on BlueStacks and feeds it into the same logic layer. The logic
layer is independent of the CV layer and is also meant to be usable
directly against Pokemon Showdown.

## Status

Early design stage. Current contents:

- [`schema/battle_state.py`](schema/battle_state.py) — the shared
  battle-state/action contract between the CV layer, a Pokemon Showdown
  environment adapter, and the model. Opponent info uses live, dynamically
  updated per-move/item/ability/tera/spread probabilities rather than
  discrete preset "sets" — see the module for the full rationale.

Next up: an environment harness wiring this schema to a local Pokemon
Showdown instance for self-play.
