"""Drive the real CLI (`app/cli_entry.py`) in a pseudo-terminal.

Ctrl-C is sent as the byte 0x03 through the pty, so the kernel's line
discipline turns it into SIGINT for the foreground process group, exactly as a
person pressing Ctrl-C in `./tariff-chat` would.
"""

from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import struct
import termios
import threading
import time

from common import PYTHON, ROOT, app_env

_ANSI = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\r")


class CliProcess:
    def __init__(self, session: str, log_file) -> None:
        self.session = session
        self.output = ""
        self._lock = threading.Lock()
        env = app_env(log_file)
        env["TERM"] = "xterm"
        env["COLUMNS"] = "160"
        pid, fd = pty.fork()
        if pid == 0:  # child
            os.chdir(ROOT)
            os.execve(
                PYTHON,
                [PYTHON, "app/cli_entry.py", "--session", session],
                env,
            )
        self.pid = pid
        self._fd = fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        while True:
            try:
                ready, _, _ = select.select([self._fd], [], [], 0.2)
                if not ready:
                    continue
                data = os.read(self._fd, 65536)
            except OSError:
                return
            if not data:
                return
            with self._lock:
                self.output += _ANSI.sub(b"", data).decode(errors="replace")

    def mark(self) -> int:
        with self._lock:
            return len(self.output)

    def since(self, mark: int) -> str:
        with self._lock:
            return self.output[mark:]

    def expect(self, pattern: str, timeout: float = 60.0, since: int = 0) -> str:
        regex = re.compile(pattern)
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                match = regex.search(self.output, since)
            if match:
                return match.group(0)
            if not self.running():
                break
            time.sleep(0.05)
        raise TimeoutError(
            f"pattern {pattern!r} not seen; tail:\n{self.output[-1500:]}"
        )

    def send(self, text: str) -> None:
        os.write(self._fd, text.encode() + b"\r")

    def ctrl_c(self) -> float:
        os.write(self._fd, b"\x03")
        return time.time()

    def running(self) -> bool:
        try:
            done, _ = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            return False
        if done:
            self._exited = True
            return False
        return not getattr(self, "_exited", False)

    def wait_exit(self, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.running():
                return True
            time.sleep(0.1)
        return False
