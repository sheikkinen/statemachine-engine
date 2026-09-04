"""FR-FSM-019 AC-02: measure control-socket event-pickup latency per tick branch.

Sends datagrams to a live engine's control socket and measures send → process_event
entry. Two scenarios per run:
  stale_non_waiting : state='listening', _last_activity_time aged 10s before each send
  fresh_non_waiting : state='listening', _last_activity_time = now before each send
"""
import asyncio
import json
import socket
import statistics
import time

from statemachine_engine.core.engine import StateMachineEngine

N = 40


async def measure(stale: bool) -> list[float]:
    name = f"fr019_{'stale' if stale else 'fresh'}"
    eng = StateMachineEngine(machine_name=name)
    eng.config = {
        "initial_state": "listening",
        "transitions": [{"from": "listening", "event": "ping", "to": "listening"}],
        "actions": {},
        "events": ["ping"],
    }
    eng.current_state = "listening"
    eng._create_control_socket()

    arrivals: list[float] = []
    orig = eng.process_event

    async def spy(event, context=None):
        if event == "ping":
            arrivals.append(time.perf_counter())
        return await orig(event, context)

    eng.process_event = spy
    task = asyncio.create_task(eng.execute_state_machine({}))
    await asyncio.sleep(0.2)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    path = f"{eng.control_socket_prefix}-{name}.sock"
    latencies: list[float] = []
    for i in range(N):
        # settle so the loop is sleeping in the branch under test
        await asyncio.sleep(0.6 + (i % 7) * 0.037)
        eng._last_activity_time = time.time() - (10.0 if stale else 0.0)
        # jitter so sends are not phase-locked to the tick
        await asyncio.sleep((i * 0.0137) % 0.5)
        before = len(arrivals)
        t0 = time.perf_counter()
        client.sendto(json.dumps({"type": "ping", "payload": {}}).encode(), path)
        while len(arrivals) == before:
            await asyncio.sleep(0.001)
        latencies.append((arrivals[-1] - t0) * 1000)

    eng.is_running = False
    await task
    client.close()
    return latencies


def report(label: str, ms: list[float]) -> None:
    ms_sorted = sorted(ms)
    p = lambda q: ms_sorted[min(len(ms_sorted) - 1, int(q * len(ms_sorted)))]
    print(
        f"{label:18s} n={len(ms)} min={ms_sorted[0]:6.1f} "
        f"p50={statistics.median(ms):6.1f} p90={p(0.9):6.1f} "
        f"max={ms_sorted[-1]:6.1f} mean={statistics.mean(ms):6.1f} ms"
    )


async def main() -> None:
    report("stale_non_waiting", await measure(stale=True))
    report("fresh_non_waiting", await measure(stale=False))


if __name__ == "__main__":
    asyncio.run(main())
