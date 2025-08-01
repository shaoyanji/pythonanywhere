# PythonAnywhere

These are some of the things to do on a flask web server hosted on [pythonanywhere](https://pythonanywhere.com)

## TODO List

- [x] tgpt webfrontend
- [ ] gutenbergcache
- [ ] upx binary caching
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
- [ ] serving html directly from mysql database, would make local development only work with full api calls
- [x] implemented doit task
- [x] initialized typer app
- [ ] began modularizing app
  - [x] ai
  - [ ] api
  - [ ] routes
  - [x] wsgi
  - [ ] html
  - [ ] database

## Limitations:

There is a [whitelist domains](https://www.pythonanywhere.com/whitelist/) which means that there are quite a lot of blacklisted services which makes a lot of CLI tools obsolete and requires some JSON Hacking in python to tease out what needs to be teased out.
500 MB storage limit. This means that it struggles hosting the blobs of binaries to make neovim tooling work. Although I managed to get a kickstarter appimage neovim installed on the server, the performance and bootup is awful.
