"""S00: one full chat-run with the fake answering everything (baseline)."""
import asyncio, sys, time
from common import FakeGeminiProcess, OUT, reset_db, run_rows, descendants, log
from cli_driver import CliProcess

async def main():
    await reset_db()
    with FakeGeminiProcess("s00") as fake:
        cli = CliProcess("s00", OUT / "s00.cli.log")
        cli.expect(r"You >", 90)
        start = time.time()
        cli.send(sys.argv[1] if len(sys.argv) > 1 else "monitor overdraft")
        try:
            cli.expect(r"\[fake\] run_tariff_monitoring returned|Review 1/|Something went wrong", 600)
        finally:
            log(cli.output[-4000:])
            log(f"elapsed {time.time()-start:.1f}s")
            for e in fake.events(): log(str(e))
            log(str(await run_rows()))
            log(str(descendants(cli.pid)))
            cli.ctrl_c(); time.sleep(0.5); cli.ctrl_c()
            cli.wait_exit(20)

asyncio.run(main())
