# Shaoyan Ji Lab

Thin Flask/Jinja rebuild for PythonAnywhere.

This project now treats the repo as a small personal publishing system instead of an open-ended experiment hub:

- public site for notes, experiments, and about pages
- private admin area for content, prompt logs, and deploy actions
- one MySQL access layer via `mysql.connector`
- SQL migrations stored in-repo
- markdown as the primary authored content format

## Product shape

Public routes:

- `/`
- `/notes`
- `/notes/<slug>`
- `/experiments`
- `/experiments/<slug>`
- `/experiments/wasm-kelly-criterion/demo`
- `/about`

Private admin routes:

- `/admin`
- `/admin/content`
- `/admin/prompts`
- `/admin/deploy`

Utility API routes:

- `/api/health`
- `/api/summary`

## Structure

```text
app/
  __init__.py
  factory.py
  config.py
  extensions.py
  models.py
  blueprints/
    public.py
    admin.py
    api.py
    experiments.py
  services/
    auth.py
    content.py
    deploy.py
    migrations.py
  templates/
    layouts/
    partials/
    pages/
  static/
    css/
migrations/
  sql/
main.py
```

Legacy runtime-confusing modules from the pre-rebuild app have been removed:

- `app/blueprint/*`
- `app/ai.py`
- `app/db.py`
- `app/init.py`

## Database model

Active tables:

- `pages`
- `posts`
- `experiments`
- `nav_items`
- `site_settings`
- `prompt_runs`
- `schema_migrations`

Migration behavior:

- `0001_core_schema.sql` creates the CMS-style schema and seeds baseline content.
- `0002_migrate_messages_to_prompt_runs.sql` prepares prompt history storage.
- the Python migration runner conditionally copies legacy `messages` rows into `prompt_runs`
- legacy `messages` is preserved as source data, but it is no longer the primary public content model

## Environment

Set these environment variables before running or deploying:

```bash
SECRET_KEY=change-me
MYSQL_USER=your_pythonanywhere_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=your_pythonanywhere_username$default
MYSQL_HOST=your_pythonanywhere_username.mysql.pythonanywhere-services.com

ADMIN_USERNAME=admin
ADMIN_PASSWORD=choose-a-separate-password

ENABLE_ADMIN_DEPLOY=0
DEPLOY_RELOAD_COMMAND="pa webapp reload"
GIT_PULL_COMMAND=
```

Notes:

- `ADMIN_PASSWORD` must be separate from database credentials.
- `ENABLE_ADMIN_DEPLOY=1` is required before `/admin/deploy` will run anything.
- `GIT_PULL_COMMAND` is optional. If unset, deploy only runs the configured reload command.

## Local usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python main.py db-upgrade
```

Run the dev server:

```bash
python main.py serve --host 127.0.0.1 --port 5000
```

You can also use Flask CLI for migrations:

```bash
flask --app app.factory:create_app db-upgrade
```

## Local verification

Commands verified in this repo during the hardening pass:

```bash
python -m unittest discover -s tests -v
python -m compileall app main.py tests
python - <<'PY'
from app.factory import create_app
app = create_app({'TESTING': True})
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    print(rule.rule, sorted(rule.methods - {'HEAD', 'OPTIONS'}))
PY
```

What the tests prove:

- public smoke routes render
- `/admin/*` requires auth
- admin mutations stay POST-only
- deploy actions are env-gated
- markdown strips unsafe HTML and script URLs
- prompt output is escaped in admin views
- migrations rerun safely and tolerate missing legacy `messages`

## PythonAnywhere deployment

`app/wsgi.py` now imports the app factory directly and derives the project root from the file location, which keeps the WSGI entry thin and portable.

Recommended deploy/update flow:

1. Pull the latest code on the PythonAnywhere host.
2. Activate the project virtualenv.
3. Run `pip install -r requirements.txt`.
4. Export or refresh `SECRET_KEY`, MySQL variables, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`.
5. Run `python main.py db-upgrade`.
6. Reload the web app from the PythonAnywhere dashboard or with `pa webapp reload`.
7. Only if you explicitly set `ENABLE_ADMIN_DEPLOY=1`, allow `/admin/deploy` to trigger the configured reload command.

Operational expectations:

- the app reconnects MySQL connections on demand with `ping(reconnect=True)`
- deployment hooks do not reuse DB credentials for authentication
- public shell execution is removed from the active app surface
- content rendering sanitizes markdown output before it reaches templates

## Deferred / intentionally thin

- no ORM or Alembic stack; migrations are SQL files plus a small Python runner
- no SPA, frontend framework, or broad HTMX layer
- no rich admin editor beyond direct markdown fields and record upserts
- no integration test against a live MySQL database in this repo
- no richer deploy workflow beyond env-gated command execution
