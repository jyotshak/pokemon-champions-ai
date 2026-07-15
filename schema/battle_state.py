"""Shared battle-state/action contract between the CV layer, the Showdown
environment adapter, and the model. Anything that produces or consumes a
battle state (screen-reader, local Showdown harness, replay parser) must
serialize to/from this shape.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field

SpeciesId = str    # e.g. "landorus-therian"
MoveId = str       # e.g. "earthquake"
ItemId = str
AbilityId = str
TeraType = str


class Status(str, Enum):
    NONE = "none"
    BRN = "brn"
    PAR = "par"
    PSN = "psn"
    TOX = "tox"
    SLP = "slp"
    FRZ = "frz"


class Weather(str, Enum):
    NONE = "none"
    SUN = "sun"
    RAIN = "rain"
    SAND = "sand"
    SNOW = "snow"


class Terrain(str, Enum):
    NONE = "none"
    ELECTRIC = "electric"
    GRASSY = "grassy"
    MISTY = "misty"
    PSYCHIC = "psychic"


class Position(str, Enum):
    """Field slot. Matters for spread-move geometry/redirection, not just bookkeeping."""
    LEFT = "left"
    RIGHT = "right"


class Boosts(BaseModel):
    atk: int = 0
    defense: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    acc: int = 0
    eva: int = 0


class MoveSlot(BaseModel):
    move: MoveId
    pp: int
    max_pp: int
    disabled: bool = False


class VolatileState(BaseModel):
    """Open bag for turn-scoped conditions (confusion, encore, taunt, leech
    seed, substitute, protect-fail-streak, etc). Kept as a name+data bag
    rather than fixed fields because the volatile list grows every
    generation and Showdown's own protocol already emits them as tagged
    strings — enumerating each as a named field would mean a schema
    migration every gen.
    """
    name: str
    turns_remaining: Optional[int] = None
    data: dict = Field(default_factory=dict)


class OwnPokemon(BaseModel):
    """Fully known — this is our team, nothing here is uncertain."""
    species: SpeciesId
    level: int = 50
    position: Optional[Position] = None   # None if benched
    fainted: bool = False

    hp: int
    max_hp: int
    status: Status = Status.NONE
    status_turns: Optional[int] = None

    stats: dict[str, int]     # final computed {atk, def, spa, spd, spe}
    boosts: Boosts = Boosts()

    ability: AbilityId
    item: Optional[ItemId] = None
    moves: list[MoveSlot]

    tera_type: Optional[TeraType] = None    # not live at Champions launch; wired for when it ships
    tera_activated: bool = False
    mega_activated: bool = False
    """`species` is updated to the mega forme id (e.g. "charizard-mega-y")
    the moment this flips true, same convention as any other in-battle
    forme change — stats/ability/typing for the new forme follow from that.
    One Mega per team per battle; whether it ends up sharing a single
    'Omni Ring' charge with Tera once Tera ships is unconfirmed, so that
    cross-mechanic constraint isn't encoded here yet.
    """

    volatiles: list[VolatileState] = Field(default_factory=list)


class WeightedOption(BaseModel):
    """A live, dynamically-updated marginal probability for one candidate
    value (move / item / ability / tera type / spread archetype) filling a
    still-unconfirmed slot.

    Deliberately *not* a discrete joint template and *not* fixed-size. The
    correlation structure that produces these numbers — role-overlap
    tendencies (Protect vs. Wide Guard), archetype co-occurrence (Calm Mind
    raising Protect/Moonblast) — is mined empirically from replay/usage data
    and lives in the belief-tracker, not in this schema; hand-authoring
    exclusivity rules here would be exactly as brittle as it sounds (real
    Aerodactyl run both, or neither). This field only carries the
    already-updated result: whatever candidates currently have non-
    negligible probability, however many that is. Low-probability tail
    options are simply omitted rather than forced into a fixed top-K —
    there is no reserved "unknown" bucket to fall outside of, since the
    pool is drawn from the full legal move/item/ability space, not a closed
    set of named templates.
    """
    value: str
    probability: float


class OpponentPokemon(BaseModel):
    species: SpeciesId
    level: int = 50
    position: Optional[Position] = None
    fainted: bool = False

    hp_pct: float             # exact HP is normally hidden; only % is shown
    status: Status = Status.NONE
    status_turns: Optional[int] = None
    boosts: Boosts = Boosts()  # visible in the battle log, so not uncertain

    revealed_moves: list[MoveId] = Field(default_factory=list)
    move_beliefs: list[WeightedOption] = Field(default_factory=list)
    """Marginal P(this move fills one of the remaining unconfirmed slots),
    for however many of the 4 move slots aren't yet in `revealed_moves`.
    Not a per-slot breakdown, and not required to sum to the remaining slot
    count exactly — it's an approximation, not a joint, and is only turned
    into a concrete point estimate (e.g. "most likely 4th move") on demand
    by the belief-tracker, via constrained argmax, not by sorting this list
    and taking the top N.
    """

    revealed_item: Optional[ItemId] = None
    item_beliefs: list[WeightedOption] = Field(default_factory=list)

    revealed_ability: Optional[AbilityId] = None
    ability_beliefs: list[WeightedOption] = Field(default_factory=list)

    tera_activated: bool = False
    revealed_tera_type: Optional[TeraType] = None
    tera_beliefs: list[WeightedOption] = Field(default_factory=list)

    mega_activated: bool = False
    """Visible/certain the instant it happens, same as tera_activated. When
    it flips true, `species` updates to the mega forme id, same convention
    as OwnPokemon — stats, and usually ability, are then whatever that new
    forme's fixed dex entry says (a species/forme-lookup, not a multiplier;
    contrast with `stat_multipliers`, which is for genuinely multiplicative
    effects like Commander). Any prior `ability_beliefs`/`spread_beliefs`
    uncertainty collapses to the mega forme's fixed ability and gets
    re-evaluated against the new forme's base stats, not the old ones.

    Pre-activation likelihood of *which* opponent mon is the team's
    designated Mega is mostly already carried by `item_beliefs`/
    `revealed_item` — a held Mega Stone has essentially no purpose other
    than mega-evolving. *When* (which turn) they'll actually activate it
    isn't belief state at all — it's a prediction about the opponent's
    in-battle decision, made by the policy/opponent-model at decision time
    from the current state (this field, item_beliefs, and
    FieldState.opp_side.mega_used), not something stored here.
    """

    spread_beliefs: list[WeightedOption] = Field(default_factory=list)
    """Candidates are spread-archetype keys (e.g. "bulky_physical_wall",
    "max_speed_max_attack"), not raw EV tuples — matches how spreads are
    actually inferred (via speed order / damage rolls narrowing down an
    archetype) rather than resolving exact numbers before they're forced.
    """

    known_stats: Optional[dict[str, int]] = None
    """Set only when exact stats become publicly certain (e.g. Transform
    copying a known OwnPokemon). Overrides belief-derived stat estimates
    entirely rather than blending with them.
    """
    stat_multipliers: dict[str, float] = Field(default_factory=dict)
    """Publicly-confirmed multiplicative modifiers outside the boost-stage
    system: Commander (Dondozo x2 atk/spa/spe while Tatsugiri commands),
    Protosynthesis/Quark Drive, Power Trick's swap, etc. These are certain,
    not probabilistic, once the engine has announced them — they layer on
    top of whatever base stats are known or believed.
    """

    volatiles: list[VolatileState] = Field(default_factory=list)


class SideConditions(BaseModel):
    reflect_turns: int = 0
    light_screen_turns: int = 0
    aurora_veil_turns: int = 0
    tailwind_turns: int = 0
    safeguard_turns: int = 0
    mist_turns: int = 0
    stealth_rock: bool = False
    spikes_layers: int = 0
    toxic_spikes_layers: int = 0
    sticky_web: bool = False

    mega_used: bool = False
    """Whether this side has already spent its one-per-battle Mega. Hoisted
    to side level rather than left as 'scan every mon's mega_activated' —
    that scan is easy to get wrong once the mon that mega'd has fainted.
    """
    tera_used: bool = False   # same idea, dormant until Tera ships


class FieldState(BaseModel):
    weather: Weather = Weather.NONE
    weather_turns: int = 0
    terrain: Terrain = Terrain.NONE
    terrain_turns: int = 0
    trick_room_turns: int = 0
    gravity_turns: int = 0
    my_side: SideConditions = SideConditions()
    opp_side: SideConditions = SideConditions()


class TeamPreviewInfo(BaseModel):
    """Species-only view available before bring/lead selection."""
    my_team: list[SpeciesId]
    opp_team: list[SpeciesId]


class BattleState(BaseModel):
    format_id: str             # e.g. "gen9vgc2026regh" — pins ruleset + move/item id space
    schema_version: str = "0.1"
    turn: int
    team_preview: Optional[TeamPreviewInfo] = None   # present only pre-battle

    field: FieldState
    my_active: list[OwnPokemon]        # len 2 in doubles, positions filled
    my_bench: list[OwnPokemon]
    opp_active: list[OpponentPokemon]
    opp_bench: list[OpponentPokemon]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class Target(str, Enum):
    OPP_LEFT = "opp_left"
    OPP_RIGHT = "opp_right"
    ALLY = "ally"
    SELF = "self"
    NONE = "none"      # spread moves / no-target moves — targeting is implicit


class MoveAction(BaseModel):
    kind: str = "move"
    move_slot: int               # 1-4
    target: Target
    tera: bool = False           # only legal if tera not yet activated this battle (not live at launch)
    mega: bool = False           # only legal if mega not yet activated this battle, and mon holds its Mega Stone


class SwitchAction(BaseModel):
    kind: str = "switch"
    bench_slot: int


class NoAction(BaseModel):
    """The slot has no decision this turn — currently only reached when a
    Pokemon is Commander-hidden and skipped in turn order entirely. Forced
    continuations (recharge, an Outrage still locked in) are NOT this case:
    a move genuinely executes, the policy just has no real choice, so those
    stay MoveAction with the legal action space constrained to one option.
    """
    kind: str = "none"


Action = Union[MoveAction, SwitchAction, NoAction]


class TurnActions(BaseModel):
    """Submitted simultaneously for both active slots; resolution order
    (who moves first) is derived from speed/priority, not chosen here.
    """
    slot_left: Action
    slot_right: Action


class TeamPreviewAction(BaseModel):
    bring: list[int]        # 4 indices into the 6-mon roster
    lead_order: list[int]   # first 2 of `bring`, in field order [left, right]
