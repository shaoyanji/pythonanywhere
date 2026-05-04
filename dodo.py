#!/usr/bin/env python
import jinja2
import os
from doit.action import CmdAction
from doit.task import clean_targets
from doit.tools import run_once

DATA_URLS = [
        'https://s3.amazonaws.com/pydoit-intermediate/Melee_data.csv.document.md.tpl',
        'https://github.com/dharmx/walls/raw/refs/heads/main/anime/a_beach_with_a_bridge_and_trees.jpg',
        'https://github.com/PDFMathTranslate/PDFMathTranslate/raw/refs/heads/main/test/file/translate.cli.font.unknown.pdf',
        'https://raw.githubusercontent.com/ryangrose/easy-pandoc-templates/refs/heads/master/css/elegant_bootstrap.css',
        'https://cdn.jsdelivr.net/npm/yorha@1.2.0/dist/yorha.min.css',
        'https://cdn.jsdelivr.net/gh/kimeiga/bahunya@css/bahunya-0.1.3.css'
        ]

def task_download_data():
    """ downloads data """
#    def print_url(URL):
#        print 'File was retrieved from: {0}'.format(URL)
    for URL in DATA_URLS:
        target = os.path.basename(URL)
        yield {'name': 'download:{0}'.format(target),
                'actions': ['curl -OL {0}'.format(URL)],
                'targets': [target],
                "uptodate": [run_once],
                "clean":[clean_targets],
                }

def task_build_markdown_file():
    """ builds the markdown file with jinja """ 
    def do_build(targets):

        with open(targets[0] + '.tpl') as fp:
            template = jinja2.Template(fp.read())

        with open(targets[0], 'w') as fp:
            fp.write(template.render(author='PandaDoctor',date="2222-01-01", heatmap_filename='a_beach_with_a_bridge_and_trees.jpg'))
    return {'actions': [do_build],
                    'file_dep': ['a_beach_with_a_bridge_and_trees.jpg', 'Melee_data.csv.document.md.tpl'],
                    'targets': ['Melee_data.csv.document.md'],
                    'clean': [clean_targets]}
def task_pandoc():
    """ uses pandoc """
    cmd = 'pandoc -t html5 -f markdown+smart --standalone --self-contained  '\
                ' -c elegant_bootstrap.css'\
                ' -s %(dependencies)s -o %(targets)s'
            #' --css=bahunya-0.1.3.css' \
            #' --css=yorha.min.css'\
           
    return {'actions': [cmd],
            'file_dep': ['Melee_data.csv.document.md',
                'elegant_bootstrap.css'
                #'yorha.min.css'
                #'bahunya-0.1.3.css'
                ],
            'targets': ['app/static/x.pdf'],
            "uptodate": [run_once],
            'clean': [clean_targets]}

def task_createdotenv():
    """load the dotenv"""
    return {
        "actions": ['age -d -i ~/.ssh/id_ed25519 %(dependencies)s > %(targets)s'], 
        "targets" : [".env"],
        "file_dep": [".env.age"],
        "uptodate": [run_once],
        "clean":[clean_targets],
        "verbosity": 2,
    }

def task_webappreload():
    """pythonanywhere reload cmd - decrypts .env.age if needed"""
    def reload_with_env(targets):
        import subprocess
        import os
        from dotenv import load_dotenv

        # Ensure .env exists by decrypting .env.age if needed
        if not os.path.exists(".env") and os.path.exists(".env.age"):
            subprocess.run(
                ["age", "-d", "-i", os.path.expanduser("~/.ssh/id_ed25519"), ".env.age"],
                stdout=open(".env", "w"),
                check=True
            )
            print("Decrypted .env.age to .env")

        # Load environment variables from .env file
        load_dotenv()

        # Run reload - pa automatically knows which webapp from the environment
        return subprocess.run(["pa", "webapp", "reload"], check=True)

    return {
        "actions": [reload_with_env],
        "file_dep": [".env.age"],
        "uptodate": ["false"],
        "verbosity": 2,
    }

def task_gitbackup():
    """backs everything up one github shell execution"""
    return {
        "actions": ["git add .", "git commit -m doitupdate", "git push"],
        "verbosity": 2,
    }

def task_destroydotenv():
    """remove the dotenv"""
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
        "uptodate" : [True] 
    }


#def task_tailwind():
#    """tailwind install with npm"""
#    return {
#        "actions": ["npm install tailwindcss @tailwindcss/cli",
#            "echo `@import 'tailwindcss';` > ./app/static/input.css","npx @tailwindcss/cli -i ./app/static/input.css -o ./app/static/output.css --watch"],
#        "targets": ["./app/static/input.css","./app/static/output.css"],
#        "verbosity": 2,
#        "uptodate" : [True] 
#    }


def task_pythondeps():
    """python deps install"""
    def installdeps():
        return "pip install -r requirements.txt"

    return {
        "actions": [CmdAction(installdeps)],
        "targets": ["requirements.txt"],
        "verbosity": 2,
        "uptodate": [True]
    }
   
