"""F6: asyncio.Runner SIGINT handling with the CLI's converse/uncancel pattern (run in a terminal, press Ctrl-C three times)."""
import asyncio, signal, sys
async def converse(i):
    turn = asyncio.create_task(asyncio.sleep(100))
    try:
        await turn
    except asyncio.CancelledError:
        if not turn.done(): turn.cancel()
        await asyncio.wait({turn})
        asyncio.current_task().uncancel()
        print(f"turn {i} cancelled; handler={signal.getsignal(signal.SIGINT)!s:.40}", flush=True)
async def main():
    for i in (1, 2, 3):
        print(f"turn {i} running", flush=True)
        await converse(i)
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt -> exit", flush=True)
