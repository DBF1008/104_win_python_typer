import os
import re
import shutil
from pathlib import Path
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Sandboxed HOME — session-scoped autouse fixture
# ---------------------------------------------------------------------------
#
# Completion-install and app-dir tests used to read/write the *real* user
# home directory (~/.bashrc, ~/.zshrc, ~/.config/fish/, etc.).  This caused:
#
#   1. Local machines getting their dotfiles mutated by the test suite.
#   2. CI runners leaving stale artefacts that polluted later jobs sharing
#      the same VM image.
#   3. Race conditions under pytest-xdist (``--numprocesses=auto``) where
#      parallel workers simultaneously rewrote the same ``~/.bashrc``.
#
# The fixture below creates a throwaway directory and redirects every
# "where is the user's home?" lookup to it:
#
#   * ``HOME`` / ``USERPROFILE`` env vars   — picked up by child processes
#     spawned via ``subprocess.run(env={**os.environ, ...})``, and by
#     CPython's own ``os.path.expanduser`` / ``Path.home()``.
#   * ``XDG_CONFIG_HOME``, ``APPDATA``, ``LOCALAPPDATA`` — used by
#     ``get_app_dir`` and various XDG-aware tools.
#   * ``pathlib.Path.home`` and ``os.path.expanduser`` — patched in the
#     current (parent) process so direct calls are sandboxed too.
#
# The fixture is **session-scoped** so the sandbox is set up once per pytest
# worker (xdist workers each get their own isolated temp directory).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _sandboxed_home(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Redirect every home-directory lookup to a throwaway temp directory."""
    sandboxed_home = tmp_path_factory.mktemp("sandboxed_home")
    str_home = str(sandboxed_home)

    # -- environment variables (propagate into subprocess children) ----------
    os.environ["HOME"] = str_home
    os.environ["USERPROFILE"] = str_home
    os.environ["XDG_CONFIG_HOME"] = str(sandboxed_home / ".config")
    os.environ["APPDATA"] = str(sandboxed_home / "AppData" / "Roaming")
    os.environ["LOCALAPPDATA"] = str(sandboxed_home / "AppData" / "Local")

    # -- in-process patches (Path.home / expanduser) --------------------------
    home_mock = mock.patch("pathlib.Path.home", return_value=sandboxed_home)
    home_mock.start()

    def _fake_expanduser(path: str) -> str:
        if not path.startswith("~"):
            return path
        rest = path[2:] if len(path) > 1 and path[1] in "/\\" else path[1:]
        sep = os.sep if rest and rest[0] not in "/\\" else ""
        return str_home + sep + rest

    expanduser_mock = mock.patch("os.path.expanduser", side_effect=_fake_expanduser)
    expanduser_mock.start()

    yield  # ── tests run here ──

    expanduser_mock.stop()
    home_mock.stop()


# ---------------------------------------------------------------------------
# Diagnostic artefacts on test failure
# ---------------------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> None:
    """Stash the latest test-phase report on the item for session-finish."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    item._test_report = report  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Copy sandboxed HOME tree into ``test-diagnostics/`` when tests fail."""
    if exitstatus == 0:
        return

    # Locate the sandboxed home for *this* pytest process.
    fake_home = Path(os.environ.get("HOME", os.environ.get("USERPROFILE", "")))
    if not fake_home.exists():
        return  # pragma: no cover

    diagnostics_root = Path("test-diagnostics")
    diagnostics_root.mkdir(exist_ok=True)

    collected = 0
    for item in session.items:
        report: pytest.TestReport | None = getattr(item, "_test_report", None)
        if report is None or report.outcome != "failed":
            continue

        safe_name = re.sub(r"[^\w\-.]", "_", item.nodeid)[:200]
        test_diag = diagnostics_root / safe_name

        if fake_home.exists():
            shutil.copytree(fake_home, test_diag / "home", dirs_exist_ok=True)

        # Persist the longrepr (traceback / assertion message).
        if report.longreprtext:
            (test_diag / "failure.txt").write_text(
                report.longreprtext, encoding="utf-8"
            )
        collected += 1

    if collected:
        # Leave a machine-readable index for CI artefact consumers.
        (diagnostics_root / "INDEX").write_text(
            f"collected {collected} failure(s) from worker pid={os.getpid()}\n",
            encoding="utf-8",
        )
