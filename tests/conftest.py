import shutil
from pathlib import Path

import pytest


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    # Stash each phase's report on the item so fixtures can inspect the outcome
    # during teardown (e.g. to capture diagnostics only when a test failed).
    rep = yield
    setattr(item, f"rep_{rep.when}", rep)
    return rep


def _dump_sandbox(home: Path, nodeid: str) -> None:  # pragma: no cover
    # Only runs when a sandboxed test failed: copy the temporary home into a
    # persistent, CI-uploadable location so the installed completion files are
    # available for debugging.
    safe_nodeid = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in nodeid)
    dest = Path("test-reports") / "sandbox" / safe_nodeid
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(home, dest)


@pytest.fixture
def sandbox_home(tmp_path, monkeypatch, request):
    """Redirect ``Path.home()`` to a per-test temporary directory.

    Completion installation writes into ``Path.home()`` (see
    ``typer/_completion_shared.py``). Setting ``HOME``/``USERPROFILE`` makes both
    the in-process ``CliRunner`` tests and the ``subprocess``-based tests (which
    inherit ``os.environ``) install into an isolated, throwaway home. This keeps
    the real home untouched and is safe under ``pytest -n auto`` because each test
    gets its own ``tmp_path``.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    yield home
    rep_setup = getattr(request.node, "rep_setup", None)
    rep_call = getattr(request.node, "rep_call", None)
    failed = (rep_setup is not None and rep_setup.failed) or (
        rep_call is not None and rep_call.failed
    )
    if failed:  # pragma: no cover
        _dump_sandbox(home, request.node.nodeid)
