"""
Regression tests for state pollution between consecutive in-process
invocations of the ``typer`` CLI entry point.

The CLI's module-level ``state`` singleton and the dynamically injected
``run`` command must be fully refreshed on every invocation so that
file / module / --app / --func selections never leak across calls.
"""

from typer.cli import app as cli_app, state
from typer.testing import CliRunner

runner = CliRunner()

# ── asset paths ────────────────────────────────────────────────────
# sample.py         : app  -> hello(name)! and bye(friend)
# multi_app.py      : app  -> top()  +  sub -> hello(name), hi(user), bye()
# multi_func.py     : plain functions: main(name), say_stuff()
# app_other_name.py : application -> callback(name)
# func_other_name.py: some_function(name)
# multi_app_cli.py  : cli  -> top()  +  sub -> hello(), bye()

SAMPLE = "tests/assets/cli/sample.py"
MULTI_APP = "tests/assets/cli/multi_app.py"
MULTI_FUNC = "tests/assets/cli/multi_func.py"
APP_OTHER = "tests/assets/cli/app_other_name.py"
FUNC_OTHER = "tests/assets/cli/func_other_name.py"
MULTI_CLI = "tests/assets/cli/multi_app_cli.py"


def _invoke(args: list[str]):
    """Invoke the CLI app in-process (same runner, same process)."""
    return runner.invoke(cli_app, args)


# ── file → different file ──────────────────────────────────────────

def test_file_then_different_file():
    """Second file's run command must not serve the first file's app."""
    # sample.py: hello outputs "Hello {name}!" (with exclamation)
    r1 = _invoke([SAMPLE, "run", "hello", "--name", "Alice"])
    assert r1.exit_code == 0
    assert "Hello Alice!" in r1.output

    # multi_app.py: has a `top` command that outputs "top"
    r2 = _invoke([MULTI_APP, "run", "top"])
    assert r2.exit_code == 0
    assert "top" in r2.output
    # Must NOT show sample.py commands like hello/bye at top level
    assert "Say hi" not in r2.output


def test_file_then_different_file_reversed():
    """Order reversed: multi_app first, then sample."""
    r1 = _invoke([MULTI_APP, "run", "top"])
    assert r1.exit_code == 0
    assert "top" in r1.output

    # sample.py: hello outputs "Hello {name}!"
    r2 = _invoke([SAMPLE, "run", "hello", "--name", "World"])
    assert r2.exit_code == 0
    assert "Hello World!" in r2.output


# ── file → no path clears state ───────────────────────────────────

def test_file_then_no_path_clears_state():
    """Calling with no path after a file call must not keep stale file."""
    _invoke([SAMPLE, "run", "hello"])
    # Calling without path_or_module should show help, not attempt to run sample.py
    r = _invoke(["--help"])
    assert r.exit_code == 0
    # The help output should NOT list "run" as an available command
    assert "Run the provided Typer app." not in r.output


# ── --app does not leak ────────────────────────────────────────────

def test_app_flag_does_not_leak():
    """--app from the first call must not affect the second call."""
    # app_other_name.py has `application` (non-default name), needs --app
    # The app has a single command `callback`, so it's flattened under `run`
    r1 = _invoke(["--app", "application", APP_OTHER, "run", "--name", "Test"])
    assert r1.exit_code == 0
    assert "Hello Test" in r1.output

    # sample.py auto-discovers `app` — no --app needed
    r2 = _invoke([SAMPLE, "run", "hello", "--name", "NoApp"])
    assert r2.exit_code == 0
    assert "Hello NoApp!" in r2.output


def test_app_flag_only_applies_to_own_call():
    """--app on first call must not leak; second call without --app
    should auto-discover the default app in a different file."""
    _invoke(["--app", "application", APP_OTHER, "run"])
    r = _invoke([SAMPLE, "run", "hello", "--name", "Auto"])
    assert r.exit_code == 0
    assert "Hello Auto!" in r.output


# ── --func does not leak ──────────────────────────────────────────

def test_func_flag_does_not_leak():
    """--func from the first call must not affect the second call."""
    # The function is wrapped as a single command under `run`
    r1 = _invoke(["--func", "some_function", FUNC_OTHER, "run", "--name", "Func"])
    assert r1.exit_code == 0
    assert "Hello Func" in r1.output

    # sample.py auto-discovers its `app` Typer
    r2 = _invoke([SAMPLE, "run", "hello", "--name", "NoFunc"])
    assert r2.exit_code == 0
    assert "Hello NoFunc!" in r2.output


# ── --app and --func mutual isolation ─────────────────────────────

def test_app_and_func_mutual_isolation():
    """Alternating --app and --func calls must not cross-contaminate."""
    # Use --app (single command, flattened under run)
    r1 = _invoke(["--app", "application", APP_OTHER, "run", "--name", "A"])
    assert r1.exit_code == 0
    assert "Hello A" in r1.output

    # Use --func (single command, flattened under run)
    r2 = _invoke(["--func", "some_function", FUNC_OTHER, "run", "--name", "B"])
    assert r2.exit_code == 0
    assert "Hello B" in r2.output

    # No flags, auto-discover Typer app
    r3 = _invoke([SAMPLE, "run", "hello", "--name", "C"])
    assert r3.exit_code == 0
    assert "Hello C!" in r3.output


# ── auto-discovery function → typer app ───────────────────────────

def test_func_autodiscovery_then_typer_app():
    """A file with only functions (auto-discovered) followed by a file
    with a Typer app must resolve correctly."""
    # multi_func.py: main(name) prints "Hello {name}"
    r1 = _invoke([MULTI_FUNC, "run", "--name", "Stuff"])
    assert r1.exit_code == 0
    assert "Hello Stuff" in r1.output

    # sample.py: hello(name) echoes "Hello {name}!"
    r2 = _invoke([SAMPLE, "run", "hello", "--name", "After"])
    assert r2.exit_code == 0
    assert "Hello After!" in r2.output


def test_typer_app_then_func_autodiscovery():
    """Typer app file followed by a function-only file."""
    r1 = _invoke([SAMPLE, "run", "hello", "--name", "First"])
    assert r1.exit_code == 0
    assert "Hello First!" in r1.output

    r2 = _invoke([MULTI_FUNC, "run", "--name", "Second"])
    assert r2.exit_code == 0
    assert "Hello Second" in r2.output


# ── different files with `cli` vs `app` variable names ────────────

def test_different_app_variable_names():
    """Files using different variable names for the Typer instance."""
    # sample.py uses `app`
    r1 = _invoke([SAMPLE, "run", "hello", "--name", "AppVar"])
    assert r1.exit_code == 0
    assert "Hello AppVar!" in r1.output

    # multi_app_cli.py uses `cli`
    r2 = _invoke([MULTI_CLI, "run", "top"])
    assert r2.exit_code == 0
    assert "top" in r2.output


# ── utils docs uses correct target ────────────────────────────────

def test_docs_targets_correct_file():
    """`utils docs` must generate docs for the current file, not a stale one."""
    r1 = _invoke([SAMPLE, "utils", "docs"])
    assert r1.exit_code == 0
    # sample.py's `app` has `hello` and `bye` commands
    assert "hello" in r1.output
    assert "bye" in r1.output

    r2 = _invoke([MULTI_APP, "utils", "docs"])
    assert r2.exit_code == 0
    # multi_app.py's `app` has `top` command and `sub` sub-typer
    assert "top" in r2.output
    # sample.py does NOT have a `top` command
    assert "top" not in r1.output


def test_docs_after_run_uses_correct_target():
    """After a `run` invocation, `utils docs` must target the new file."""
    _invoke([SAMPLE, "run", "hello", "--name", "X"])

    r = _invoke([MULTI_APP, "utils", "docs"])
    assert r.exit_code == 0
    assert "top" in r.output


def test_docs_then_run_different_files():
    """docs for one file then run for another file."""
    r1 = _invoke([MULTI_APP, "utils", "docs"])
    assert r1.exit_code == 0
    assert "top" in r1.output

    r2 = _invoke([SAMPLE, "run", "hello", "--name", "Y"])
    assert r2.exit_code == 0
    assert "Hello Y!" in r2.output


# ── state object is clean after each call ─────────────────────────

def test_state_reset_between_calls():
    """Verify the module-level state reflects the last invocation only."""
    _invoke([SAMPLE, "run", "hello"])
    _invoke([MULTI_APP, "run", "top"])
    # state.file should point to MULTI_APP, not SAMPLE
    assert state.file is not None
    assert str(state.file).endswith("multi_app.py")


def test_state_cleared_when_no_path_given():
    """When no path_or_module is given, state must not retain old values."""
    _invoke([SAMPLE, "run", "hello"])
    _invoke(["--help"])
    assert state.file is None
    assert state.module is None
    assert state.app is None
    assert state.func is None


# ── three consecutive calls ───────────────────────────────────────

def test_three_consecutive_different_files():
    """Three back-to-back calls to three different files."""
    r1 = _invoke([SAMPLE, "run", "hello", "--name", "One"])
    assert r1.exit_code == 0
    assert "Hello One!" in r1.output

    r2 = _invoke([MULTI_FUNC, "run", "--name", "Two"])
    assert r2.exit_code == 0
    assert "Hello Two" in r2.output

    r3 = _invoke([MULTI_APP, "run", "top"])
    assert r3.exit_code == 0
    assert "top" in r3.output


def test_run_then_help_then_run_different():
    """Interleaving run and help with different files."""
    r1 = _invoke([SAMPLE, "run", "hello", "--name", "First"])
    assert r1.exit_code == 0
    assert "Hello First!" in r1.output

    r2 = _invoke([MULTI_APP, "--help"])
    assert r2.exit_code == 0
    assert "run" in r2.output

    r3 = _invoke([MULTI_APP, "run", "top"])
    assert r3.exit_code == 0
    assert "top" in r3.output
