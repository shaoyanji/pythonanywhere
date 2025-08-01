from doit.action import CmdAction

def default():
    def menu():
        return "doit $(doit list | awk '{print $1}'| fzf)"
    return {
            'actions': [CmdAction(menu)],
            'verbosity': 2,
            }

def task_webappreload():
    """pythonanywhere reload cmd """

    def create_cmd_string():
        return "age -d -i ~/.ssh/id_ed25519 .env.age > .env && pa webapp reload"

    return {
        'actions': [CmdAction(create_cmd_string)],
        'verbosity': 2,
    }


def task_hello():
    """it writes hello in a hello.txt in the git repo"""

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {
        'actions': [python_hello],
        'targets': ["hello.txt"],
    }


def task_gitbackup():
    """backs everything up one github"""

    def create_cmd_string():
        return "git add . &&git commit -m doitupdate && git push -u"
    return {
        'actions': [CmdAction(create_cmd_string)],
        'verbosity': 2,
    }
