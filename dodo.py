from doit.action import CmdAction


def task_m():
    """doit $(doit list | fzf | awk '{print $1}'"""

    def create_cmd_string():
        return "echo doit list "

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_webappreload():
    """pythonanywhere reload cmd"""

    def create_cmd_string():
        return "age -d -i ~/.ssh/id_ed25519 .env.age > .env && pa webapp reload"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_hello():
    """it writes hello in a hello.txt in the git repo"""

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {
        "actions": [python_hello],
        "targets": ["hello.txt"],
    }


def task_gitbackup():
    """backs everything up one github"""

    def create_cmd_string():
        return "git add . &&git commit -m doitupdate && git push -u"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_exit():
    """get out"""

    def create_cmd_string():
        return "exit"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_llm():
    """export environment and then groq"""

    def create_cmd_string():
        return "export $(age -d -i ~/.ssh/id_ed25519 .env.age) && tgpt -i --provider groq --key $GROQ_API_KEY --model llama3-70b-8192"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_tailwind():
    """tailwind install with npm"""

    def create_cmd_string():
        return "which npm"

    #        return "npm install tailwindcss @tailwindcss/cli && echo '@import "tailwindcss";' > ./static/input.css && npx @tailwindcss/cli -i ./static/input.css -o ./static/output.css --watch"
    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }


def task_pythondeps():
    """python deps install"""

    def create_cmd_string():
        return "pip install -r requirements.txt"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "verbosity": 2,
    }
