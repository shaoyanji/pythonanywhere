#!/usr/bin/env python
import jinja2
import os
from doit.action import CmdAction
from doit.task import clean_targets
from doit.tools import run_once

DATA_URLS = [
        'https://s3.amazonaws.com/pydoit-intermediate/Melee_data.csv.document.md.tpl'
        'https://github.com/PDFMathTranslate/PDFMathTranslate/raw/refs/heads/main/test/file/translate.cli.font.unknown.pdf'
        ]

def task_download_data():
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
    
    def do_build(targets):

        with open(targets[0] + '.tpl') as fp:
            template = jinja2.Template(fp.read())

        with open(targets[0], 'w') as fp:
            fp.write(template.render(author='PandaDoctor',date="2222-01-01", file='translate.cli.font.unknown.pdf'))
    return {'actions': [do_build],
                    'file_dep': ['translate.cli.font.unknown.pdf', 'Melee_data.csv.document.md.tpl'],
                    'targets': ['Melee_data.csv.document.md'],
                    'clean': [clean_targets]}
def task_pandoc():
    cmd = 'pandoc -f markdown -t html'\
            ' -s %(dependencies)s -o %(targets)s'
    return {'actions': [cmd],
            'file_dep': ['Melee_data.csv.document.md'],
            'targets': ['app/static/x.pdf'],
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
    """pythonanywhere reload cmd"""
    return {
        "actions": ["pa webapp reload"],
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
   
