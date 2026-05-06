#!/usr/bin/env python
import os
import sys
from pathlib import Path


def _maybe_enable_debugpy() -> None:
    """Open a debugpy port (5678) when DEBUGPY=1 is set.

    Off by default so production and normal local runs don't pay the
    import cost or expose a debugger port. Set DEBUGPY_WAIT=1 to also
    block until VS Code attaches — useful when you need to break before
    Django finishes booting.
    """
    if os.environ.get("DEBUGPY") != "1":
        return
    # Skip when we're not actually running a long-lived process. There's no
    # point opening the port for one-shot commands like `manage.py shell -c`.
    if len(sys.argv) > 1 and sys.argv[1] not in ("runserver", "test"):
        return
    # Django's runserver autoreload spawns two processes (watcher + worker)
    # and only the worker has RUN_MAIN=true. If autoreload is on we have to
    # listen only in the worker, otherwise the second process crashes with
    # EADDRINUSE. With --noreload there's just one process and we listen
    # straight away.
    autoreload_on = sys.argv[1] == "runserver" and "--noreload" not in sys.argv
    if autoreload_on and os.environ.get("RUN_MAIN") != "true":
        return
    import debugpy

    debugpy.listen(("0.0.0.0", 5678))  # noqa: S104 — must bind on the container's external interface so the host's VS Code can connect
    if os.environ.get("DEBUGPY_WAIT") == "1":
        print("⏳ debugpy listening on :5678, waiting for client...", flush=True)
        debugpy.wait_for_client()
        print("✅ debugger attached", flush=True)
    else:
        print("⚙️  debugpy listening on :5678 (attach when you want)", flush=True)


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings.dev")

    _maybe_enable_debugpy()

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
