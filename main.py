#!/usr/bin/env python
import typer

from app.factory import create_app
from app.services.migrations import migrate_database


cli = typer.Typer()


@cli.command()
def serve(host: str = "127.0.0.1", port: int = 5000, debug: bool = True):
    app = create_app()
    app.run(host=host, port=port, debug=debug)


@cli.command("db-upgrade")
def db_upgrade():
    app = create_app()
    with app.app_context():
        migrate_database()
    print("Database migrations applied.")


if __name__ == "__main__":
    cli()
