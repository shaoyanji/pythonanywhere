from __future__ import annotations

import shlex
import subprocess

from flask import current_app


def run_command(command_text: str) -> dict[str, object]:
    result = subprocess.run(
        shlex.split(command_text),
        check=False,
        text=True,
        capture_output=True,
    )
    return {
        "command": command_text,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }


def run_deploy_tasks() -> list[dict[str, object]]:
    if not current_app.config["ENABLE_ADMIN_DEPLOY"]:
        return [
            {
                "command": "deploy",
                "returncode": 1,
                "stdout": "",
                "stderr": "Deploy actions are disabled. Set ENABLE_ADMIN_DEPLOY=1 to enable them.",
                "ok": False,
            }
        ]

    results = []
    pull_command = current_app.config["GIT_PULL_COMMAND"]
    if pull_command:
        results.append(run_command(pull_command))
    results.append(run_command(current_app.config["DEPLOY_RELOAD_COMMAND"]))
    return results

