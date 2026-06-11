"""Test fixture with rich tags, ANSI codes, and colons in help text."""
import typer

app = typer.Typer()


@app.command()
def deploy(
    env: str = typer.Option(
        "prod",
        help="Target [bold]environment[/]: staging, prod, or dev",
    ),
):
    """Deploy to an environment."""
    print(f"Deploying to {env}")


@app.command()
def status(
    service: str = typer.Option(
        "all",
        help="Service name (e.g. [cyan]api[/]: [green]running[/])",
    ),
):
    """Check service status."""
    print(f"Status: {service}")


@app.command()
def configure(
    setting: str = typer.Option(
        "default",
        help="Config key: value pair (e.g. [yellow]timeout[/]: 30)",
    ),
):
    """Configure application settings."""
    print(f"Configured: {setting}")


if __name__ == "__main__":
    app()
