import inspect


def clean_help_text(
    text: str | None,
    *,
    markup_mode: str | None = None,
    first_paragraph_only: bool = False,
) -> str:
    """Normalize help/docstring text into a single, consistent form.

    This is the shared entry point for help-text cleaning used by the three
    output paths (terminal command help, shell completion, and ``docs``
    export) so that they all apply the same rules:

    * dedent with :func:`inspect.cleandoc`
    * drop everything after a ``\\f`` form-feed marker
    * strip the ``\\b`` no-rewrap marker while keeping that paragraph's own
      line breaks
    * collapse single line breaks into spaces, but only for Rich markup mode
      (Markdown / no-markup output is left untouched for the downstream
      renderer)

    Args:
        text: The raw help string (or ``None``).
        markup_mode: ``"rich"``, ``"markdown"`` or ``None``. Single line breaks
            are only collapsed when this is ``"rich"``.
        first_paragraph_only: If ``True``, keep only the first paragraph (used
            for short, one-line help such as the subcommand listing).
    """
    if not text:
        return ""
    # Remove indentation from the (possibly triple-quoted) source string.
    text = inspect.cleandoc(text)
    # Trim off anything that comes after a "\f" form feed.
    text = text.partition("\f")[0]
    paragraphs = text.split("\n\n")
    if first_paragraph_only:
        paragraphs = paragraphs[:1]
    cleaned_paragraphs: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith("\b"):
            # "\b" marks a paragraph that must not be rewrapped: drop the
            # marker (and the newline right after it) but keep the rest of its
            # internal line breaks.
            cleaned_paragraphs.append(paragraph.lstrip("\b").lstrip("\n"))
        elif markup_mode == "rich":
            # Rich does not treat single line breaks as paragraph separators.
            cleaned_paragraphs.append(paragraph.replace("\n", " "))
        else:
            cleaned_paragraphs.append(paragraph)
    return "\n\n".join(cleaned_paragraphs).strip()
