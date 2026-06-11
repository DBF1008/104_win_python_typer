import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import shellingham
from typer.testing import CliRunner

from docs_src.typer_app import tutorial001_py310 as mod

from ..utils import requires_completion_permission

runner = CliRunner()
app = mod.app


@requires_completion_permission
def test_completion_install_no_shell(sandbox_home):
    result = subprocess.run(
        [sys.executable, "-m", "coverage", "run", mod.__file__, "--install-completion"],
        capture_output=True,
        encoding="utf-8",
        env={
            **os.environ,
            "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "True",
        },
    )
    assert "Option '--install-completion' requires an argument" in result.stderr, (
        result.stdout
    )


@requires_completion_permission
def test_completion_install_bash(sandbox_home):
    bash_completion_path: Path = sandbox_home / ".bashrc"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            mod.__file__,
            "--install-completion",
            "bash",
        ],
        capture_output=True,
        encoding="utf-8",
        env={
            **os.environ,
            "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "True",
        },
    )
    new_text = bash_completion_path.read_text()
    install_source = Path(".bash_completions/tutorial001_py310.py.sh")
    assert str(install_source) in new_text
    assert "completion installed in" in result.stdout, result.stderr
    assert "Completion will take effect once you restart the terminal" in result.stdout
    install_source_path = sandbox_home / install_source
    assert install_source_path.is_file()
    install_content = install_source_path.read_text()
    assert (
        "complete -o default -F _tutorial001_py310py_completion tutorial001_py310.py"
        in install_content
    )


@requires_completion_permission
def test_completion_install_zsh(sandbox_home):
    completion_path: Path = sandbox_home / ".zshrc"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            mod.__file__,
            "--install-completion",
            "zsh",
        ],
        capture_output=True,
        encoding="utf-8",
        env={
            **os.environ,
            "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "True",
        },
    )
    new_text = completion_path.read_text()
    zfunc_fragment = "fpath+=~/.zfunc"
    assert zfunc_fragment in new_text
    assert "completion installed in" in result.stdout, result.stderr
    assert "Completion will take effect once you restart the terminal" in result.stdout
    install_source_path = sandbox_home / ".zfunc/_tutorial001_py310.py"
    assert install_source_path.is_file()
    install_content = install_source_path.read_text()
    assert (
        "compdef _tutorial001_py310py_completion tutorial001_py310.py"
        in install_content
    )


@requires_completion_permission
def test_completion_install_fish(sandbox_home):
    script_path = Path(mod.__file__)
    completion_path: Path = (
        sandbox_home / f".config/fish/completions/{script_path.name}.fish"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            mod.__file__,
            "--install-completion",
            "fish",
        ],
        capture_output=True,
        encoding="utf-8",
        env={
            **os.environ,
            "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "True",
        },
    )
    new_text = completion_path.read_text()
    assert "complete --command tutorial001_py310.py" in new_text
    assert "completion installed in" in result.stdout, result.stderr
    assert "Completion will take effect once you restart the terminal" in result.stdout


@requires_completion_permission
def test_completion_install_powershell(sandbox_home):
    completion_path: Path = (
        sandbox_home / ".config/powershell/Microsoft.PowerShell_profile.ps1"
    )
    completion_path_bytes = f"{completion_path}\n".encode("windows-1252")

    with mock.patch.object(
        shellingham, "detect_shell", return_value=("pwsh", "/usr/bin/pwsh")
    ):
        with mock.patch.object(
            subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                ["pwsh"], returncode=0, stdout=completion_path_bytes
            ),
        ):
            result = runner.invoke(app, ["--install-completion"])
    install_script = "Register-ArgumentCompleter -Native -CommandName mocked-typer-testing-app -ScriptBlock $scriptblock"
    parent: Path = completion_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(install_script)
    new_text = completion_path.read_text()
    assert install_script in new_text
    assert "completion installed in" in result.stdout, result.stderr
    assert "Completion will take effect once you restart the terminal" in result.stdout
