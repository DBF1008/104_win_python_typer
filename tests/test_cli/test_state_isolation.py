"""Regression tests for state leaking between consecutive in-process CLI calls.

The Typer CLI keeps the selected entrypoint (file/module) and object (app/func)
in a module level ``state`` singleton. When the CLI is invoked several times in
the same Python process (as happens in test suites), a previous selection used
to leak into the next call, e.g. a previously chosen file would shadow a newly
given module, or a previously chosen ``--app`` would shadow a new ``--func``,
pointing both ``run`` and ``utils docs`` at the stale object.

All tests below invoke the CLI twice in the same process and assert the second
call resolves the correct object. Note the ``--app``/``--func`` options are
top-level options of the CLI group, so they must precede the path/module
argument on the command line.
"""

from typer.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_file_does_not_leak_into_following_module():
    # First call selects a file entrypoint (sample.py, default ``app``).
    first = runner.invoke(app, ["tests/assets/cli/sample.py", "run", "hello"])
    assert first.exit_code == 0, first.output
    assert "Hello World!" in first.output

    # Second call selects a *module* entrypoint with a different object. If the
    # previous file leaked, it would shadow the module (file is preferred over
    # module) and "top" would not be found.
    second = runner.invoke(app, ["tests.assets.cli.multi_app", "run", "top"])
    assert second.exit_code == 0, second.output
    assert "top" in second.output
    assert "Hello World!" not in second.output


def test_app_selection_does_not_leak_into_following_func():
    # First call selects an object via --app.
    first = runner.invoke(
        app, ["--app", "app", "tests/assets/cli/multi_app.py", "run", "top"]
    )
    assert first.exit_code == 0, first.output
    assert "top" in first.output

    # Second call selects a *function* via --func on a module that has no ``app``
    # attribute. If the stale --app leaked, lookup would fail with
    # "Not a Typer object: --app app".
    second = runner.invoke(
        app, ["--func", "say_stuff", "tests/assets/cli/multi_func.py", "run"]
    )
    assert second.exit_code == 0, second.output
    assert "Stuff" in second.output
    assert "Not a Typer object" not in second.output


def test_func_selection_does_not_leak_into_following_default_app():
    # First call selects an object via --func.
    first = runner.invoke(
        app, ["--func", "say_stuff", "tests/assets/cli/multi_func.py", "run"]
    )
    assert first.exit_code == 0, first.output
    assert "Stuff" in first.output

    # Second call relies on the default app resolution. If the stale --func
    # leaked, it would try to load "say_stuff" from multi_app and fail with
    # "Not a function: --func say_stuff".
    second = runner.invoke(app, ["tests/assets/cli/multi_app.py", "run", "top"])
    assert second.exit_code == 0, second.output
    assert "top" in second.output
    assert "Not a function" not in second.output


def test_app_and_func_swap_between_entrypoints():
    # --func entrypoint first, then a --app entrypoint. Neither selection field
    # may survive across the boundary.
    first = runner.invoke(
        app, ["--func", "some_function", "tests/assets/cli/func_other_name.py", "run"]
    )
    assert first.exit_code == 0, first.output
    assert "Hello World" in first.output

    second = runner.invoke(
        app, ["--app", "application", "tests/assets/cli/app_other_name.py", "run"]
    )
    assert second.exit_code == 0, second.output
    assert "Hello World" in second.output
    assert "Not a function" not in second.output


def test_docs_not_polluted_by_previous_run():
    # A previous ``run`` against a file must not make ``utils docs`` generate
    # docs for the stale object instead of the freshly given module.
    first = runner.invoke(app, ["tests/assets/cli/sample.py", "run", "bye"])
    assert first.exit_code == 0, first.output
    assert "Goodbye" in first.output

    second = runner.invoke(app, ["tests.assets.cli.multi_app", "utils", "docs"])
    assert second.exit_code == 0, second.output
    # Docs must describe multi_app (Demo App with a ``top`` command), not the
    # previous sample.py (whose ``hello`` had a ``--formal`` option that
    # multi_app's does not).
    assert "Demo App" in second.output
    assert "top" in second.output
    assert "--formal" not in second.output
