"""Test fixture with autocompletion returning rich tags, ANSI codes, and colons."""
import typer

image_desc = [
    ("alpine:latest", "latest [green]alpine[/] image"),
    ("alpine:hello", "fake image: with [bold]rich[/] and: colons"),
    ("nvidia/cuda:10.0", "\x1b[31mansi\x1b[0m colored desc"),
    ("registry:5000/app", "multiline\nhelp\twith\ttabs"),
]


def _complete(incomplete: str) -> str:
    for image, desc in image_desc:
        if image.startswith(incomplete):
            yield image, desc


app = typer.Typer()


@app.command()
def image(name: str = typer.Option(autocompletion=_complete)):
    typer.echo(name)


if __name__ == "__main__":
    app()
