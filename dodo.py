from doit.action import CmdAction


def task_createdotenv():
    """load the dotenv"""
    return {
        "actions": ['age -d -i ~/.ssh/id_ed25519 %(dependencies)s > .env'], 
        "targets" : [".env"],
        "file_dep": [".env.age"],
        "verbosity": 2,
    }

def task_webappreload():
    """pythonanywhere reload cmd"""

    return {
        "actions": ["pa webapp reload"],
        "file_dep":[".env"],
        "verbosity": 2,
    }

 

def task_gitbackup():
    """backs everything up one github shell execution"""

    return {
        "actions": ["git add .", "git commit -m doitupdate", "git push"],
        "verbosity": 2,
    }

def task_destroydotenv():
    """load the dotenv"""
    return {
        "actions": ['rm .env'], 
        "verbosity": 2,
    }

def task_exit():
    """get out"""

    return {
        "actions": ["exit"],
        "verbosity": 2,
    }
def task_m():
    """doit $(doit list | fzf | awk '{print $1}'"""
    return {
        "actions": ["doit list"],
        "verbosity": 2,
        "uptodate": [True]
    }
def task_hello():
    """it writes hello in a hello.txt in the git repo"""

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {
        "actions": [python_hello],
        "targets": ["hello.txt"],
        "uptodate": [True]
    }


def task_llm():
    """export environment and then groq"""
    return {
        "actions": ["export $(age -d -i ~/.ssh/id_ed25519 .env.age) && tgpt -i --provider groq --key $GROQ_API_KEY --model openai/gpt-oss-20b"],
        "file_dep": [".env.age"],
        "verbosity": 2,
    }


def task_tailwind():
    """tailwind install with npm"""

    return {
        "actions": ["npm install tailwindcss @tailwindcss/cli",
            "echo `@import 'tailwindcss';` > ./app/static/input.css","npx @tailwindcss/cli -i ./app/static/input.css -o ./app/static/output.css --watch"],
        "targets": ["./app/static/input.css","./app/static/output.css"],
        "verbosity": 2,
        "uptodate" : [True] 
    }


def task_pythondeps():
    """python deps install"""
    def create_cmd_string():
        return "pip install -r requirements.txt"

    return {
        "actions": [CmdAction(create_cmd_string)],
        "targets": ["requirements.txt"],
        "verbosity": 2,
        "uptodate": [True]
    }
   
