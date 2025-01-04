from doit.action import CmdAction


def task_hello():
    """hello cmd """

    def create_cmd_string():
        return "pa webapp reload"

    return {
        'actions': [CmdAction(create_cmd_string)],
        'verbosity': 2,
    }


def task_hello2():
    """hello"""

    def python_hello(targets):
        with open(targets[0], "a") as output:
            output.write("Python says Hello World!!!\n")

    return {
        'actions': [python_hello],
        'targets': ["hello.txt"],
    }
