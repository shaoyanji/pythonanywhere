#!/usr/bin/env python
import typer
import app.ai

cli = typer.Typer()

defaultprompt = "output in ansi:"


@cli.command()
def bot(message: str, prompt: str = defaultprompt):
    response = app.ai.aiflow(prompt, message)
    print(f"{response}")


@cli.command()
def shell(cmd: str):
    response = app.shellcmd(f"{cmd}")
    print(f"{response}")


@cli.command()
def groq(message: str):
    response = app.ai.groq_handler(message)
    print(f"{response}")


@cli.command()
def cohere(message: str):
    response = app.ai.cohere_handler(message)
    print(f"{response}")


@cli.command()
def gemini(message: str):
    response = app.ai.gemini_handler(message)
    print(f"{response}")


if __name__ == "__main__":
    cli()
