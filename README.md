# PythonAnywhere

These are some of the things to do on a flask web server hosted on [pythonanywhere](https://pythonanywhere.com)

## TODO List

- [ ] build a partial html api segment
- [x] modularized db
- [x] add the monospace tree to the navbar
- [x] tgpt webfrontend
- [ ] gutenbergcache
- [ ] upx binary caching
- [ ] scraping
    - [ ] htmlq cache
    - [ ] sec.gov reader
    - [ ] pdfgrepper alongside --htmlq--
- [ ] tgpt --img image generator
- [ ] github stuff
- [ ] wikipedia.org
- [ ] age and age-keygen server
- [x] update neovim https://github.com/neovim/neovim-releases/releases
- [x] curlified the main api
- [x] added shell capabilities
- [x] made css agnostic to utilize [cssbed](cssbed.com)'s list of classless styles. Current one is yorha.
- [x] serving html/API state from mysql-backed endpoints for orchestrator-compatible CLI storage
- [x] implemented doit task
- [x] initialized typer app
- [x] pandoc pdf generator from dodo.py
- [ ] implement a simple wasm entry
- [ ] began modularizing app
    - [x] ai
    - [ ] api
    - [ ] routes
    - [x] wsgi
    - [ ] html
    - [x] database
    - [x] nerdfonts
    - [x] fork awesome font for lighterweight icons

## Limitations:

There is a [whitelist domains](https://www.pythonanywhere.com/whitelist/) which means that there are quite a lot of blacklisted services which makes a lot of CLI tools obsolete and requires some JSON Hacking in python to tease out what needs to be teased out.
500 MB storage limit. This means that it struggles hosting the blobs of binaries to make neovim tooling work. Although I managed to get a kickstarter appimage neovim installed on the server, the performance and bootup is awful.

## MySQL API endpoints (orchestrator-compatible)

Under `app/blueprint/api.py` with blueprint prefix `/api/v1`:

- `GET /api/v1/health`
- `GET|POST|PUT|DELETE /api/v1/messages`
- `GET /api/v1/orchestrator/tasks`
- `POST /api/v1/orchestrator/tasks` (upsert)
- `PATCH /api/v1/orchestrator/tasks/<task_id>`
- `GET /api/v1/orchestrator/events`
- `POST /api/v1/orchestrator/events`

Authentication for mutating orchestrator endpoints uses HTTP Basic with:
- username: `MYSQL_USER`
- password: `MYSQL_PASSWORD`

Tables are auto-initialized on request in `app/db.py`:
- `messages`
- `orchestrator_tasks`
- `orchestrator_events`
