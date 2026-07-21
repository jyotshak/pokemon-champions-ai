"""Named teams for testing — separate from harness/doubles_smoke_test.py's
TEAM (our own solver's team) so we can start pairing DIFFERENT teams
against each other instead of only ever mirror-matching (see docs/
solver_design.md and memory: the mirror-match testing gap found
2026-07-18 — team preview is deterministic given a roster, so identical
rosters on both sides meant team-building never differentiated solver
from heuristic in any test run so far).

TEAM_LOPUNNY_TR: the real opponent team observed via harness/
play_vs_solver.py (2026-07-18) — Lopunny/Farigiraf/Kingambit/Ceruledge/
Drampa/Sylveon, a Trick-Room-leaning build. Verified fully champions-legal
against reference/ data (species, items, abilities, and every move
checked against each mon's actual learnset) before being trusted here.

TEAM_AERO_HO / TEAM_SWAMPERT_TR: user-provided pastes (2026-07-18) for
add_ev_spreads validation — Tailwind hyper-offense vs a Trick-Room/
weather-support build. Neither paste had EVs (or, per add_ev_spreads'
docstring, real natures to check against — the site's nature field was
already broken); every mon here does carry a real Nature from the user,
so add_ev_spreads only ever exercises its EVs-insertion path on these
two, not its nature-inference fallback.
"""

from harness.team_paste import add_ev_spreads, add_level

TEAM_LOPUNNY_TR = add_level("""
Lopunny @ Lopunnite
Ability: Limber
EVs: 32 Atk / 32 Spe
Jolly Nature
- Protect
- Close Combat
- Fake Out
- After You

Farigiraf @ Sitrus Berry
Ability: Armor Tail
EVs: 22 HP / 17 Def / 27 SpD
Bold Nature
- Helping Hand
- Trick Room
- Thunderbolt
- Twin Beam

Kingambit @ Chople Berry
Ability: Defiant
EVs: 32 HP / 32 Atk
Adamant Nature
- Protect
- Kowtow Cleave
- Sucker Punch
- Iron Head

Ceruledge @ Focus Sash
Ability: Flash Fire
EVs: 32 HP / 21 Atk / 13 Def
Adamant Nature
- Protect
- Bulk Up
- Shadow Sneak
- Bitter Blade

Drampa @ Life Orb
Ability: Cloud Nine
EVs: 32 HP / 10 Def / 20 SpA / 4 SpD
Modest Nature
- Protect
- Hyper Voice
- Earth Power
- Draco Meteor

Sylveon @ Fairy Feather
Ability: Pixilate
EVs: 26 HP / 13 Def / 27 SpA
Modest Nature
- Detect
- Hyper Voice
- Hyper Beam
- Quick Attack
""")

TEAM_AERO_HO = add_level(add_ev_spreads("""
Aerodactyl @ Aerodactylite
Ability: Unnerve
Jolly Nature
- Rock Slide
- Ice Fang
- Tailwind
- Wide Guard

Kingambit @ Focus Sash
Ability: Defiant
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Iron Head
- Protect

Sylveon @ Fairy Feather
Ability: Pixilate
Modest Nature
- Detect
- Hyper Voice
- Hyper Beam
- Quick Attack

Garchomp @ Life Orb
Ability: Rough Skin
Jolly Nature
- Earthquake
- Dragon Claw
- Stomping Tantrum
- Protect

Charizard @ Charizardite Y
Ability: Blaze
Modest Nature
- Protect
- Heat Wave
- Solar Beam
- Weather Ball

Incineroar @ Sitrus Berry
Ability: Intimidate
Impish Nature
- Darkest Lariat
- Flare Blitz
- Fake Out
- Parting Shot
"""))

TEAM_SWAMPERT_TR = add_level(add_ev_spreads("""
Grimmsnarl @ Light Clay
Ability: Prankster
Careful Nature
- Foul Play
- Parting Shot
- Reflect
- Light Screen

Swampert @ Swampertite
Ability: Damp
Adamant Nature
- Wave Crash
- Earthquake
- Ice Punch
- Protect

Pelipper @ Sitrus Berry
Ability: Drizzle
Modest Nature
- Hurricane
- Weather Ball
- Tailwind
- Wide Guard

Archaludon @ Leftovers
Ability: Stamina
Modest Nature
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Protect

Sinistcha @ Colbur Berry
Ability: Hospitality
Relaxed Nature
- Matcha Gotcha
- Rage Powder
- Trick Room
- Protect

Metagross @ Metagrossite
Ability: Clear Body
Jolly Nature
- Iron Head
- Psychic Fangs
- Body Press
- Protect
"""))
