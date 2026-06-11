"""End-to-end completion-install tests that write into a temporary directory.

These tests exercise the full ``--install-completion`` path (subprocess → CLI
→ shell-specific installer) while redirecting all filesystem writes to a
``tmp_path`` via the ``_TYPER_COMPLETE_INSTALL_DIR`` environment variable.
They are safe to run in CI without the ``_TYPER_RUN_INSTALL_COMPLETION_TESTS``
gate and never touch the real user home directory.
"""

import os
import subprocess
import sys
from pathlib import Path

from docs_src.typer_app import tutorial001_py310 as mod

PROG_NAME = "tutorial001_py310.py"


def _run_install(shell: str, tmp_dir: Path) -> subprocess.CompletedProcess[str]:
    """Invoke ``--install-completion <shell>`` with the tmp dir override."""
    # Ensure the project root is importable so the subprocess can ``import typer``.
    project_root = str(Path(__file__).resolve().parents[2])
    python_path = os.environ.get("PYTHONPATH", "")
    python_path = f"{project_root}{os.pathsep}{python_path}" if python_path else project_root

    env = {
        **os.environ,
        "PYTHONPATH": python_path,
        "_TYPER_COMPLETE_INSTALL_DIR": str(tmp_dir),
        "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "True",
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            mod.__file__,
            "--install-completion",
            shell,
        ],
        capture_output=True,
        encoding="utf-8",
        env=env,
    )


# ── bash ──────────────────────────────────────────────────────────────────────


def test_install_bash_tmpdir(tmp_path: Path) -> None:
    result = _run_install("bash", tmp_path)
    assert result.returncode == 0, result.stderr

    # .bashrc was created inside tmp_path and contains a source line that
    # points to the completion script (also inside tmp_path).
    bashrc = tmp_path / ".bashrc"
    assert bashrc.is_file()
    bashrc_text = bashrc.read_text()

    completion_script = tmp_path / ".bash_completions" / f"{PROG_NAME}.sh"
    assert completion_script.is_file()
    assert f"source '{completion_script}'" in bashrc_text

    # The completion script itself carries the expected ``complete`` directive.
    script_text = completion_script.read_text()
    assert (
        "complete -o default -F _tutorial001_py310py_completion tutorial001_py310.py"
        in script_text
    )

    # Stdout carries the standard user-facing messages.
    assert "completion installed in" in result.stdout
    assert "Completion will take effect once you restart the terminal" in result.stdout

    # Nothing was written outside tmp_path.
    real_bashrc = Path.home() / ".bashrc"
    real_completion_dir = Path.home() / ".bash_completions"
    # If the real .bashrc exists, it must not reference our tmp script.
    if real_bashrc.is_file():
        assert str(completion_script) not in real_bashrc.read_text()
    # The real completion dir must not contain our file (it may not exist at all).
    assert not (real_completion_dir / f"{PROG_NAME}.sh").is_file()


# ── zsh ───────────────────────────────────────────────────────────────────────


def test_install_zsh_tmpdir(tmp_path: Path) -> None:
    result = _run_install("zsh", tmp_path)
    assert result.returncode == 0, result.stderr

    zshrc = tmp_path / ".zshrc"
    assert zshrc.is_file()
    zshrc_text = zshrc.read_text()

    # fpath must point to the *absolute* zfunc dir inside tmp_path so that
    # the completion is loadable regardless of what $HOME is.
    zfunc_dir = tmp_path / ".zfunc"
    assert f"fpath+={zfunc_dir}" in zshrc_text
    assert "autoload -Uz compinit; compinit" in zshrc_text

    # The zstyle helper line is present (fresh .zshrc → no prior zstyle).
    assert "zstyle ':completion:*' menu select" in zshrc_text

    completion_script = zfunc_dir / f"_{PROG_NAME}"
    assert completion_script.is_file()
    script_text = completion_script.read_text()
    assert (
        "compdef _tutorial001_py310py_completion tutorial001_py310.py" in script_text
    )

    assert "completion installed in" in result.stdout
    assert "Completion will take effect once you restart the terminal" in result.stdout

    # Nothing leaked into the real home directory.
    real_zfunc = Path.home() / ".zfunc" / f"_{PROG_NAME}"
    assert not real_zfunc.is_file()


# ── fish ──────────────────────────────────────────────────────────────────────


def test_install_fish_tmpdir(tmp_path: Path) -> None:
    result = _run_install("fish", tmp_path)
    assert result.returncode == 0, result.stderr

    completion_script = (
        tmp_path / ".config" / "fish" / "completions" / f"{PROG_NAME}.fish"
    )
    assert completion_script.is_file()
    script_text = completion_script.read_text()
    assert f"complete --command {PROG_NAME}" in script_text

    assert "completion installed in" in result.stdout
    assert "Completion will take effect once you restart the terminal" in result.stdout

    # Nothing leaked.
    real_fish = (
        Path.home() / ".config" / "fish" / "completions" / f"{PROG_NAME}.fish"
    )
    assert not real_fish.is_file()


# ── idempotency ───────────────────────────────────────────────────────────────


def test_install_bash_idempotent_tmpdir(tmp_path: Path) -> None:
    """Running install twice must not duplicate the source line in .bashrc."""
    _run_install("bash", tmp_path)
    result = _run_install("bash", tmp_path)
    assert result.returncode == 0, result.stderr

    bashrc_text = (tmp_path / ".bashrc").read_text()
    completion_script = tmp_path / ".bash_completions" / f"{PROG_NAME}.sh"
    source_line = f"source '{completion_script}'"
    assert bashrc_text.count(source_line) == 1


def test_install_zsh_idempotent_tmpdir(tmp_path: Path) -> None:
    """Running install twice must not duplicate the fpath line in .zshrc."""
    _run_install("zsh", tmp_path)
    result = _run_install("zsh", tmp_path)
    assert result.returncode == 0, result.stderr

    zshrc_text = (tmp_path / ".zshrc").read_text()
    zfunc_dir = tmp_path / ".zfunc"
    fpath_line = f"fpath+={zfunc_dir}; autoload -Uz compinit; compinit"
    assert zshrc_text.count(fpath_line) == 1
