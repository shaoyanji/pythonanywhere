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
        subprocess.run(["pa", "webapp", "reload"], check=True)
        return True

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
   


# ---------------------------------------------------------------------------
# Resume editor
# ---------------------------------------------------------------------------
# Five public tasks, everything else internal and reachable only as a
# dependency. RESUME_TASKS is the single source for the Needle catalogue:
# app/services/resume/tooling.py parses *this file* to emit tools.json, so the
# router and the task runner cannot disagree about what exists.
#
# doit rejects unknown keys on a task dict ("Task x contains invalid field"), so
# the metadata lives here instead of inside each return value. Each entry must
# name a task function in this file that tooling.py can see, and every one of
# those functions must appear either in RESUME_TASKS or in RESUME_INTERNAL —
# that pairing is what makes the closed namespace checkable.
RESUME_TASKS = {
    "analyze_job": {
        "desc": "Score a job description against the resume and write proposals",
        "summary": "Deterministic match: synonym groups, stemming, TF-IDF cosine at 0.15. Writes variants/<v>/proposals.json with resume_key, evidence, score and a null suggested_change, plus the gaps that must not be invented.",
        "when_to_use": "You have a job description and want to know which existing resume lines already answer it.",
        "when_not_to_use": "You want prose rewritten, or a model's opinion. This reads phrases, not intent.",
        "inputs": ["PYANY_VARIANT (required)", "PYANY_JD or PYANY_JD_FILE (required)"],
        "outputs": ["variants/<v>/proposals.json"],
        "preconditions": ["variant name matches ^[a-z0-9][a-z0-9-]{0,39}$"],
        "example": "PYANY_VARIANT=acme PYANY_JD='We need Golang and observability' doit analyze_job",
    },
    "apply_approved": {
        "desc": "Fold approved proposals into the variant resume",
        "summary": "Writes variants/<v>/resume.json from variants/<v>/approved.json and nothing else. Without approved.json it fails before touching the filesystem, which is the gate that stops an unreviewed edit.",
        "when_to_use": "After a human has approved proposals and filled in suggested_change.",
        "when_not_to_use": "Before approval, or to force an edit through. There is no override flag on purpose.",
        "inputs": ["PYANY_VARIANT (required)"],
        "outputs": ["variants/<v>/resume.json", "variants/<v>/applied.json"],
        "preconditions": ["variants/<v>/approved.json exists with at least one item"],
        "example": "PYANY_VARIANT=acme doit apply_approved",
    },
    "build_pdf": {
        "desc": "Render the variant resume to a validated PDF with pdfcpu",
        "summary": "resume.json to pdfcpu JSON to create, validate, optimize. Writes variants/<v>/build/resume.pdf and status.json; fails on a validate error rather than serving a broken file.",
        "when_to_use": "After apply_approved, when you need the PDF to preview or download.",
        "when_not_to_use": "To check analysis results, or before the resume has any approved content.",
        "inputs": ["PYANY_VARIANT (required)"],
        "outputs": ["variants/<v>/build/resume.pdf", "variants/<v>/build/status.json", "variants/<v>/build/resume.pdfcpu.json"],
        "preconditions": ["pdfcpu on PATH or at ~/.local/bin/pdfcpu", "variants/<v>/resume.json exists, or the base resume does"],
        "example": "PYANY_VARIANT=acme doit build_pdf",
    },
    "start_dev": {
        "desc": "Start the local Flask dev server in the background",
        "summary": "Spawns main.py serve on PYANY_PORT (default 5001) and writes its pid. Refuses on PythonAnywhere, where a second server would only burn the CPU quota.",
        "when_to_use": "Working locally and you want the editor reachable on a port.",
        "when_not_to_use": "On the PythonAnywhere host, or anywhere the site is already served.",
        "inputs": ["PYANY_PORT (optional, default 5001)"],
        "outputs": [".doit-dev-server.pid"],
        "preconditions": ["not running on PythonAnywhere"],
        "example": "doit start_dev",
    },
    "show_tasks": {
        "desc": "Print the five catalogue commands Needle can route",
        "summary": "Reads the generated tools.json and prints name, scope and a runnable example. This is the task a router calls to discover what exists.",
        "when_to_use": "You forgot the exact command name, or you are checking that a name is in the catalogue.",
        "when_not_to_use": "To run a task. It only prints.",
        "inputs": [],
        "outputs": ["stdout only"],
        "preconditions": ["tools.json exists (doit tools_json)"],
        "example": "doit show_tasks",
    },
}

#: Reachable through task_dep and by hand, never through the Needle catalogue.
RESUME_INTERNAL = ("tools_json", "install_pdfcpu")

RESUME_ROOT = os.path.dirname(os.path.abspath(__file__))


def _resume_env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"{name} is required (see: doit show_tasks)")
    return value


def _resume_context():
    from app.factory import create_app

    overrides = {"RESUME_VARIANT": _resume_env("PYANY_VARIANT", "")}
    # Test hook: point the whole task surface at a scratch directory instead of
    # the checkout's variants/ without changing the app's defaults.
    scratch = os.environ.get("PYANY_VARIANTS_DIR")
    if scratch:
        overrides["RESUME_VARIANTS_DIR"] = scratch
    return create_app(overrides)


def _inside_app(action):
    """Run an action inside a Flask app context, which the services require."""
    app = _resume_context()
    with app.app_context():
        return action()


def _action_analyze_job():
    from app.services.resume import analysis, store

    variant = _resume_env("PYANY_VARIANT", required=True)
    jd_text = _resume_env("PYANY_JD", "")
    jd_file = _resume_env("PYANY_JD_FILE", "")
    if not jd_text and jd_file:
        with open(jd_file, encoding="utf-8") as handle:
            jd_text = handle.read()
    if not jd_text.strip():
        raise RuntimeError("PYANY_JD or PYANY_JD_FILE must supply job description text")

    def run():
        resume = store.load_variant(variant) or store.load_base()
        result = analysis.analyze_job(jd_text, resume)
        store.save_proposals(variant, {"jd": jd_text, **result})
        print(f"threshold {result['threshold']}  concepts {len(result['jd_concepts'])}  "
              f"proposals {len(result['proposals'])}  gaps {len(result['gaps'])}")
        for proposal in result["proposals"]:
            print(f"  {proposal['score']:.3f}  {proposal['requirement']!r} -> {proposal['resume_key']}")
        for gap in result["gaps"]:
            print(f"  GAP      {gap['requirement']!r} ({gap['evidence']})")
        return result

    return _inside_app(run)


def _action_apply_approved():
    from app.services.resume import store

    variant = _resume_env("PYANY_VARIANT", required=True)

    def run():
        try:
            result = store.apply_approved(variant)
        except store.ApprovalRequired as error:
            print(f"refused: {error}")
            raise
        for item in result["results"]:
            print(f"  {item['status']:8} {item.get('to', item.get('reason', ''))}  {item['resume_key']}")
        print(f"wrote variants/{variant}/resume.json")
        return result

    return _inside_app(run)


def _action_build_pdf():
    from app.services.resume import pdf

    variant = _resume_env("PYANY_VARIANT", required=True)

    def run():
        status = pdf.build_pdf(variant)
        print(f"pages {status['pages']}  bytes {status['size_bytes']}  validate {status['validate']}")
        print(f"wrote variants/{variant}/build/resume.pdf")
        return status

    return _inside_app(run)


def _action_start_dev():
    import subprocess
    import sys

    if os.environ.get("PYTHONANYWHERE_SITE") or os.environ.get("PYTHONANYWHERE_DOMAIN"):
        print("refused: this is the PythonAnywhere host, the site is already served there")
        raise RuntimeError("start_dev is a local task")
    port = _resume_env("PYANY_PORT", "5001")
    pidfile = os.path.join(RESUME_ROOT, ".doit-dev-server.pid")
    if os.path.exists(pidfile):
        with open(pidfile, encoding="utf-8") as handle:
            existing = handle.read().strip()
        print(f"already running (pid {existing}) or stale; remove {pidfile} to force")
        return existing
    process = subprocess.Popen(
        [sys.executable, "main.py", "serve", "--port", port],
        cwd=RESUME_ROOT,
        start_new_session=True,
    )
    with open(pidfile, "w", encoding="utf-8") as handle:
        handle.write(str(process.pid))
    print(f"dev server pid {process.pid} on http://127.0.0.1:{port}")
    return process.pid


def _action_show_tasks():
    from app.services.resume import tooling

    data = tooling.load_tools()
    for tool in data["tools"]:
        print(f"{tool['name']:16} {tool['desc']}")
        print(f"{'':16} example: {tool['example']}")
    # doit accepts True/None/string/dict from a python action; a list is rejected
    # with "It must return: False for failed task" even though nothing failed.
    return True


def _action_tools_json():
    from app.services.resume import tooling

    data = tooling.write_tools_json()
    print(f"wrote tools.json with {len(data['tools'])} tools")
    return data


def _action_install_pdfcpu():
    from app.services.resume import pdf

    # ensure_pdfcpu reads config (PDFCPU_BIN), so it needs the app context too.
    binary = _inside_app(pdf.ensure_pdfcpu)
    print(f"pdfcpu available: {binary}")
    return binary


def task_analyze_job():
    """score a job description against the resume"""
    return {"actions": [_action_analyze_job], "doc": RESUME_TASKS["analyze_job"]["desc"], "verbosity": 2}


def task_apply_approved():
    """fold approved proposals into the variant resume"""
    return {"actions": [_action_apply_approved], "doc": RESUME_TASKS["apply_approved"]["desc"], "verbosity": 2}


def task_build_pdf():
    """render the variant resume to a validated PDF"""
    return {
        "actions": [_action_build_pdf],
        "task_dep": ["install_pdfcpu"],
        "doc": RESUME_TASKS["build_pdf"]["desc"],
        "verbosity": 2,
    }


def task_start_dev():
    """run the dev server locally"""
    return {"actions": [_action_start_dev], "doc": RESUME_TASKS["start_dev"]["desc"], "verbosity": 2}


def task_show_tasks():
    """print the Needle catalogue"""
    return {"actions": [_action_show_tasks], "doc": RESUME_TASKS["show_tasks"]["desc"], "verbosity": 2}


def task_tools_json():
    """regenerate tools.json from this file (internal)"""
    # No `uptodate: [True]` here: that marks the task up to date and skips the
    # action entirely, so the catalogue would never be written.
    return {"actions": [_action_tools_json], "verbosity": 2}


def task_install_pdfcpu():
    """ensure the pdfcpu binary exists (internal)"""
    # Idempotent and cheap (a PATH lookup when present), so it runs every time
    # instead of being pinned up to date and going stale after a cleanup.
    return {"actions": [_action_install_pdfcpu], "verbosity": 2}
