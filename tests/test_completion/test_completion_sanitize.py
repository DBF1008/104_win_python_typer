"""Regression tests for completion help sanitization and escaping.

These cover help strings that mix Rich markup, ANSI escape sequences, colons,
and long/multi-line text. Such strings used to truncate the description or break
a whole group of candidates in Zsh and Fish (a stray newline introduced by Rich
wrapping, an unstripped ANSI sequence, or colon escaping undone by Rich
rendering). The output of each shell's ``format_completion`` must stay on a
single line, drop Rich markup and ANSI, and keep the existing per-shell escaping
of Bash and PowerShell intact.
"""

import pytest
from typer._click.shell_completion import CompletionItem
from typer._completion_classes import (
    BashComplete,
    FishComplete,
    PowerShellComplete,
    ZshComplete,
)

# Shells that render the help string (Bash never emits help).
HELP_SHELLS = [ZshComplete, FishComplete, PowerShellComplete]

LONG_RICH_HELP = (
    "Delete a user with [bold]USERNAME[/] from the production database "
    "after confirming the destructive operation twice to be totally safe"
)
LONG_PLAIN = (
    "Delete a user with USERNAME from the production database "
    "after confirming the destructive operation twice to be totally safe"
)
ANSI_HELP = "\x1b[1mBold\x1b[0m and \x1b[31mred\x1b[0m text"
MULTILINE_HELP = "line one\n\n   line two\twith tabs"


def _fmt(cls: type, value: str, help: str | None = None) -> str:
    instance = cls.__new__(cls)  # format_completion does not need __init__ state
    return instance.format_completion(CompletionItem(value, help=help))


@pytest.mark.parametrize("cls", HELP_SHELLS)
@pytest.mark.parametrize("help_text", [LONG_RICH_HELP, ANSI_HELP, MULTILINE_HELP])
def test_help_completion_is_single_line(cls: type, help_text: str) -> None:
    # A newline anywhere would break Zsh's `(( ... ))` array and Fish's
    # newline-separated candidate list, dropping the whole group.
    out = _fmt(cls, "delete", help_text)
    assert "\n" not in out


@pytest.mark.parametrize("cls", HELP_SHELLS)
def test_rich_tags_are_stripped(cls: type) -> None:
    out = _fmt(cls, "delete", "Delete a [bold]user[/] with [red]USERNAME[/red].")
    assert "[bold]" not in out
    assert "[red]" not in out
    assert "[/red]" not in out
    assert "Delete a user with USERNAME." in out


@pytest.mark.parametrize("cls", HELP_SHELLS)
def test_ansi_escapes_are_stripped(cls: type) -> None:
    out = _fmt(cls, "delete", ANSI_HELP)
    assert "\x1b" not in out
    assert "[1m" not in out
    assert "[31m" not in out
    assert "Bold and red text" in out


@pytest.mark.parametrize("cls", HELP_SHELLS)
def test_long_help_is_not_truncated(cls: type) -> None:
    # The full description must survive; previously it was cut at the wrap point.
    out = _fmt(cls, "delete", LONG_RICH_HELP)
    assert LONG_PLAIN in out


@pytest.mark.parametrize("cls", HELP_SHELLS)
def test_internal_whitespace_is_collapsed(cls: type) -> None:
    out = _fmt(cls, "delete", "many     spaces\tand\ttabs")
    assert "many spaces and tabs" in out


def test_zsh_escapes_colon_in_help() -> None:
    out = _fmt(ZshComplete, "delete", "format name: value:here")
    # Zsh uses ':' as a field separator, so colons in help must be escaped.
    assert r"format name\\: value\\:here" in out
    assert "\n" not in out


def test_zsh_escapes_colon_in_value() -> None:
    out = _fmt(ZshComplete, "alpine:hello", "fake image: for testing")
    assert r'"alpine\\:hello"' in out
    assert r"fake image\\: for testing" in out


def test_zsh_rich_and_colon_combined() -> None:
    # The reported case: Rich markup *and* a colon in the same help string.
    out = _fmt(ZshComplete, "img", "[bold]format[/] name:tag for an image")
    assert "[bold]" not in out
    assert r"format name\\:tag for an image" in out
    assert "\n" not in out


def test_fish_preserves_colon_and_tab_structure() -> None:
    out = _fmt(FishComplete, "alpine:hello", "fake image: for testing")
    # Fish keeps colons literal and uses exactly one tab between value and help.
    assert out == "alpine:hello\tfake image: for testing"
    assert out.count("\t") == 1
    assert "\\:" not in out


def test_fish_help_has_no_extra_tabs_or_newlines() -> None:
    out = _fmt(FishComplete, "delete", MULTILINE_HELP)
    value, _, help_part = out.partition("\t")
    assert value == "delete"
    assert "\t" not in help_part
    assert "\n" not in help_part


def test_powershell_preserves_colon() -> None:
    out = _fmt(PowerShellComplete, "alpine:hello", "fake image: for testing")
    assert out == "alpine:hello:::fake image: for testing"
    assert "\\:" not in out


def test_powershell_help_placeholder_when_empty() -> None:
    # No help -> a single space placeholder so the ':::' split stays valid.
    out = _fmt(PowerShellComplete, "alpine:hello")
    assert out == "alpine:hello::: "


def test_bash_emits_value_only() -> None:
    # Bash must be unaffected: it never includes help text in its output.
    out = _fmt(BashComplete, "alpine:hello", "fake image: for testing")
    assert out == "alpine:hello"
    assert ":::" not in out
    assert "\t" not in out
