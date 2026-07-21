"""A persistent pool of EngineBridge worker processes, for parallel MCCFR
(docs/solver_design.md - parallel engine workers). Created once per match
(subprocess startup has real cost - spawning node + loading the sim
module - so workers are reused across every decision in a battle, not
spun up fresh each time), closed once at the end.

Deliberately dumb: just N independent EngineBridge instances. All the
actual parallelization logic (splitting iterations, dispatching solves
across workers, merging regret tables) lives in model/solver_game.py,
which only depends on this pool exposing `.bridges`. Model/ still never
imports engine/ directly - callers (harness/) own both the pool and the
solver_game functions that consume it.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from engine.bridge import EngineBridge


class EngineBridgePool:
    def __init__(self, format_id: str, n_workers: int, node: str = "node"):
        if n_workers < 1:
            raise ValueError("n_workers must be >= 1")
        # Threaded, not sequential: each EngineBridge.__init__ does a
        # blocking `ping` RPC to fail fast if the sim can't load, and
        # starting node processes one at a time would make pool startup
        # cost scale with n_workers instead of happening concurrently.
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            self.bridges: list[EngineBridge] = list(
                ex.map(lambda _: EngineBridge(format_id, node=node), range(n_workers))
            )

    def __len__(self) -> int:
        return len(self.bridges)

    def close(self) -> None:
        for bridge in self.bridges:
            bridge.close()

    def __enter__(self) -> "EngineBridgePool":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
