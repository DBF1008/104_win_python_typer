from importlib.machinery import ModuleSpec
from unittest.mock import patch

import pytest
from typer._completion_classes import _sanitize_help_text


@pytest.mark.parametrize(
    "find_spec, help_text, expected",
    [
        (
            ModuleSpec("rich", loader=None),
            "help text without rich tags",
            "help text without rich tags",
        ),
        (
            None,
            "help text without rich tags",
            "help text without rich tags",
        ),
        (
            ModuleSpec("rich", loader=None),
            "help [bold]with[/] rich tags",
            "help with rich tags",
        ),
        (
            None,
            "help [bold]with[/] rich tags",
            "help [bold]with[/] rich tags",
        ),
        # ANSI escape sequences are stripped when rich is available.
        (
            ModuleSpec("rich", loader=None),
            "\x1b[1mBold\x1b[0m and \x1b[31mred\x1b[0m text",
            "Bold and red text",
        ),
        # Newlines and runs of whitespace collapse to single spaces so the
        # result stays on one line for shell completion.
        (
            ModuleSpec("rich", loader=None),
            "first line\n\nsecond   line\twith tabs",
            "first line second line with tabs",
        ),
        # Rich markup plus a newline in the same string.
        (
            ModuleSpec("rich", loader=None),
            "[bold]Title[/]\nbody text",
            "Title body text",
        ),
        # Colons are preserved by sanitization (per-shell escaping happens later).
        (
            ModuleSpec("rich", loader=None),
            "format name: value:here",
            "format name: value:here",
        ),
        # Even without rich, whitespace is still collapsed to keep a single line.
        (
            None,
            "a\n\nb   c",
            "a b c",
        ),
        (
            None,
            "[bold]x[/]\ny",
            "[bold]x[/] y",
        ),
    ],
)
def test_sanitize_help_text(
    find_spec: ModuleSpec | None, help_text: str, expected: str
):
    with patch("importlib.util.find_spec", return_value=find_spec) as mock_find_spec:
        assert _sanitize_help_text(help_text) == expected
    mock_find_spec.assert_called_once_with("rich")
