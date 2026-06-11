import os
import subprocess
import sys
from pathlib import Path


def test_doc():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets/cli/multiapp-docs.md"
    docs = docs_path.read_text()
    assert docs in result.stdout
    assert "**Arguments**" in result.stdout


def test_doc_output(tmp_path: Path):
    out_file: Path = tmp_path / "out.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--output",
            str(out_file),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets/cli/multiapp-docs.md"
    docs = docs_path.read_text()
    written_docs = out_file.read_text()
    assert docs in written_docs
    assert "Docs saved to:" in result.stdout


def test_doc_title_output(tmp_path: Path):
    out_file: Path = tmp_path / "out.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--title",
            "Awesome CLI",
            "--output",
            str(out_file),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets/cli/multiapp-docs-title.md"
    docs = docs_path.read_text()
    written_docs = out_file.read_text()
    assert docs in written_docs
    assert "Docs saved to:" in result.stdout


def test_doc_no_rich():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app_norich",
            "utils",
            "docs",
            "--name",
            "multiapp",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets/cli/multiapp-docs.md"
    docs = docs_path.read_text()
    assert docs in result.stdout
    assert "**Arguments**" in result.stdout


def test_doc_not_existing():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "no_typer",
            "utils",
            "docs",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert "Could not import as Python module:" in result.stderr


def test_doc_no_typer():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests/assets/cli/empty_script.py",
            "utils",
            "docs",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert "No Typer app found" in result.stderr


def test_doc_file_not_existing():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "assets/cli/not_existing.py",
            "utils",
            "docs",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert "Not a valid file or Python module:" in result.stderr


def test_doc_html_output(tmp_path: Path):
    out_file: Path = tmp_path / "out.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.rich_formatted_app",
            "utils",
            "docs",
            "--title",
            "Awesome CLI",
            "--output",
            str(out_file),
        ],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    docs_path: Path = (
        Path(__file__).parent.parent / "assets" / "cli" / "richformattedapp-docs.md"
    )
    docs = docs_path.read_text(encoding="utf-8")
    written_docs = out_file.read_text(encoding="utf-8")
    assert docs in written_docs
    assert "Docs saved to:" in result.stdout


def test_doc_txt():
    """Plain text format via module path produces stable, markup-free output."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--format",
            "txt",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets" / "cli" / "multiapp-docs.txt"
    docs = docs_path.read_text()
    assert docs in result.stdout
    # Must NOT contain Markdown syntax
    assert "**" not in result.stdout
    assert "```" not in result.stdout
    assert "`" not in result.stdout
    # Must contain plain section labels
    assert "Arguments:" in result.stdout
    assert "Options:" in result.stdout
    assert "Commands:" in result.stdout


def test_doc_txt_output(tmp_path: Path):
    """Plain text docs can be written to a file."""
    out_file: Path = tmp_path / "out.txt"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--format",
            "txt",
            "--output",
            str(out_file),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets" / "cli" / "multiapp-docs.txt"
    docs = docs_path.read_text()
    written_docs = out_file.read_text()
    assert docs in written_docs
    assert "Docs saved to:" in result.stdout
    assert "**" not in written_docs


def test_doc_txt_rich_stripped():
    """Rich markup tags are stripped in plain text format, content preserved."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.rich_formatted_app",
            "utils",
            "docs",
            "--title",
            "Awesome CLI",
            "--format",
            "txt",
        ],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    docs_path: Path = (
        Path(__file__).parent.parent / "assets" / "cli" / "richformattedapp-docs.txt"
    )
    docs = docs_path.read_text(encoding="utf-8")
    assert docs in result.stdout
    # Rich markup tags must be stripped — raw tag syntax must not appear
    assert "[bold" not in result.stdout
    assert "[/bold]" not in result.stdout
    assert "[red]" not in result.stdout
    assert "[green]" not in result.stdout
    assert "<span" not in result.stdout
    # But the text content must be preserved
    assert "hello" in result.stdout
    assert "cool" in result.stdout
    assert "user" in result.stdout
    assert "message" in result.stdout


def test_doc_txt_file_path():
    """File path entry point produces the same plain text as module path."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests/assets/cli/multi_app.py",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--format",
            "txt",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    docs_path: Path = Path(__file__).parent.parent / "assets" / "cli" / "multiapp-docs.txt"
    docs = docs_path.read_text()
    assert docs in result.stdout


def test_doc_txt_recursive_structure():
    """Plain text format recursively includes subcommand structure with indentation."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "typer",
            "tests.assets.cli.multi_app",
            "utils",
            "docs",
            "--name",
            "multiapp",
            "--format",
            "txt",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    stdout = result.stdout
    # Root command
    assert "multiapp" in stdout
    # First-level subcommands present
    assert "multiapp top" in stdout
    assert "multiapp sub" in stdout
    # Second-level subcommands (nested under sub) present with indentation
    assert "multiapp sub hello" in stdout
    assert "multiapp sub hi" in stdout
    assert "multiapp sub bye" in stdout
    # Indentation hierarchy: deeper commands have more leading spaces
    lines = stdout.splitlines()
    top_line = next(l for l in lines if l.strip() == "multiapp top")
    hello_line = next(l for l in lines if l.strip() == "multiapp sub hello")
    # "multiapp sub hello" should be indented more than "multiapp top"
    assert len(hello_line) - len(hello_line.lstrip()) > len(top_line) - len(
        top_line.lstrip()
    )
    # Usage strings include full command path
    assert "$ multiapp sub hello [OPTIONS]" in stdout
    assert "$ multiapp top [OPTIONS]" in stdout
