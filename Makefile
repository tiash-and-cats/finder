.DELETE_ON_ERROR:
.DEFAULT_GOAL := run

ifeq ($(OS),Windows_NT)
VENV_BIN=./env/Scripts
else
VENV_BIN=./env/bin
endif

ifneq ($(wildcard Makefile.secret),)
include Makefile.secret
# A Makefile.secret must define:
# - export DJANGO_SECRET_KEY = a secret key that Django uses
# - export OPENROUTER_KEY = the OpenRouter API key for Find4U
else
$(warning No Makefile.secret detected. You can choose to create one using the Makefile.secret rule. Or you can make it yourself.)
endif

# Shorthand help syntax
+h=sentinel
ifeq ($(+h),)
%:
	@$(MAKE) help "ON=$(MAKECMDGOALS)" --no-print-directory +h=sentinel
else

# Installs dependencies.
#
# Use the `SYS_PYTHON` variable to tell it which Python to use to create the
# virtual environment.
#
# If the `env` directory doesn't exist, it creates a Python virtual
# environment called `env`.
#
# If the `node_modules` directory doesn't exist, it executes
# `'npm init --init-type module -y'` and installs `zod` and `commander.js`
# for generating the docs for the Find4U CLI.
#
# If the `find4u/cli/node_modules` folder doesn't exist but
# `find4u/cli/ink-app/src` does, it goes into `find4u/cli` and runs
# `'npm install'`.
#
# If the `find4u/cli/ink-app/node_modules` folder doesn't exist but
# `find4u/cli/ink-app/src` does, it goes into `find4u/cli/ink-app` and runs
# `'npm install'`.
#
# If the `find4u/web/node_modules` folder doesn't exist, it goes into
# `find4u/web` and runs `'npm install'`.
#
# :variables: SYS_PYTHON
SYS_PYTHON=python
deps:
	@if [ ! -d env ]; then \
		$(SYS_PYTHON) -m venv env; \
		$(VENV_BIN)/pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu; \
		$(VENV_BIN)/pip install $(if $(filter Windows_NT,$(OS)),winloop,uvloop); \
	fi
	@if [ ! -d node_modules ]; then \
		npm init --init-type module -y; \
		npm install --no-package-lock zod commander; \
	fi
	@if [ ! -d find4u/cli/node_modules ] && [ -d find4u/cli/ink-app/src ]; then \
		cd find4u/cli; \
		npm install; \
	fi
	@if [ ! -d find4u/cli/ink-app/node_modules ] && [ -d find4u/cli/ink-app/src ]; then \
		cd find4u/cli/ink-app; \
		npm install; \
	fi
	@if [ ! -d find4u/web/node_modules ]; then \
		cd find4u/web; \
		npm install; \
	fi

# Migrate Finder database.
build-finder-db:
	cd finder_proj && .$(VENV_BIN)/python manage.py migrate

# Build Find4U static files.
build-find4u:
	cd find4u/web && npm run build

# Build documentation.
build-docs:
	source $(VENV_BIN)/activate && cd docs && make

# Generate finder-buildinfo.py.
#
# finder_buildinfo.py is how `'make run'` embeds build info in the `Via:`
# header in production.
build-finder_buildinfo:
	python finder_buildinfo.generate.py

# Build all static files and migrate Finder database.
#
# NOTE: This rule uses `'make deps'` to install dependencies before running.
#
# This runs `'make build-finder-db'`, `'make build-find4u'`, `'make build-docs'`,
# and `'make build-finder_buildinfo'`.
build: deps build-finder-db build-find4u build-docs build-finder_buildinfo

# Start the production server.
#
# (!!) Will fail without Makefile.secret. Please run 'make Makefile.secret' first.
#
# Use `PORT` to change the port the server runs on. Defaults to `80` if neither
# `SSL_KEYFILE` nor `SSL_CERTFILE` are provided, otherwise `443`.
#
# The default logging levels are:
#     - `'make'`: `INFO`
#     - `'uvicorn.error'`: `INFO`
#     - `'uvicorn.access'`: `WARNING`
#     - everything else: `WARNING`
#
# To adjust the logging, use `LOGGING_LEVEL`. You can pass four types of
# strings to it:
#
#   - `Legacy mode:` A single logging level string[1], only controlling the `make`
#     logger used by the reverse proxy.
#
#     Example: `make run LOGGING_LEVEL=DEBUG`
#
#   - `Comma-separated form:` A string of the form `'name=LEVEL, ...'` where
#     `name` is the name of a logger and LEVEL is a logging level string[1].
#
#     Example: `make run LOGGING_LEVEL="httpx=DEBUG,make=DEBUG"`
#
#   - `The string "RESET":` Do not use the default logging levels listed above
#     and just make the logging.basicConfig default `WARNING`.
#
#   - `Empty string:` Use the default logging levels listed above.
#
# `LOGGING_LEVEL` defaults to the empty string.
#
# NOTE: For `"RESET"`, other modules might change their logger's levels from
# NOTE: the logging.basicConfig default, for example `'uvicorn'`.
#
# By default, it uses `winloop` on Windows, `uvloop` on POSIX, and `asyncio`
# elsewhere as the event loop. Set `USE_ASYNCIO_LOOP` to any non-empty value
# to force the standard `asyncio` loop, regardless of OS. You don't need to
# understand this to run it, don't worry.
#
# (!!) "0" is considered truthy by Python, so 'USE_ASYNCIO_LOOP=0' will
# (!!) force asyncio. Use 'USE_ASYNCIO_LOOP='.
#
# NOTE: Setting `'USE_ASYNCIO_LOOP='` will not "force uvloop/winloop". It
# NOTE: simply means that `asyncio` will not be forced.
#
# SSL_KEYFILE and SSL_CERTFILE are for configuring SSL/TLS. Both are optional,
# but if one is present, the other should be too. SSL_KEYFILE should be set
# to the SSL key and SSL_CERTFILE should be set to the SSL certificate.
#
# An alternative approach would be to keep the core server insecure and
# put a simple HTTPS-to-HTTP proxy in front; in fact, this is what the
# official deployment at https://finder-locw.onrender.com/ does.
#
# For more technical details, see `'make help ON=Makefile_run.py'`.
#
# [1] A logging level string is a string that describes the logging level.
#     Possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
#
# :variables: LOGGING_LEVEL PORT USE_ASYNCIO_LOOP SSL_KEYFILE SSL_CERTFILE
PORT=
LOGGING_LEVEL=
USE_ASYNCIO_LOOP=
run: deps
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	@# Run the Python runner
	LOGGING_LEVEL=$(LOGGING_LEVEL) PORT=$(PORT) USE_ASYNCIO_LOOP=$(USE_ASYNCIO_LOOP) \
	SSL_KEYFILE=$(SSL_KEYFILE) SSL_CERTFILE=$(SSL_CERTFILE) $(VENV_BIN)/python Makefile_run.py

# Interactively creates a Makefile.secret file.
#
# NOTE: This rule uses 'make deps' to install dependencies before running.
Makefile.secret: | deps
	$(VENV_BIN)/python Makefile.secret.generate.py

# Build a Docker image.
#
# Use the `DOCKER_IMAGE_NAME` variable to set the image name (defaults to `finder`).
#
# :variables: DOCKER_IMAGE_NAME
DOCKER_IMAGE_NAME=finder
docker-build:
	docker build -t $(DOCKER_IMAGE_NAME) .

# Run the Docker image built with `'make docker-build'`.
#
# Use `DOCKER_IMAGE_NAME` to set the image name (default: `finder`).
#
# PROTIP: Use `'make -n docker-run'` to see the command to run the image without
# actually running the image.
#
# :variables: DOCKER_IMAGE_NAME
docker-run:
	docker run -p 80:80 -e OPENROUTER_KEY='$(OPENROUTER_KEY)' -e DJANGO_SECRET_KEY=$(DJANGO_SECRET_KEY) $(DOCKER_IMAGE_NAME)

# Show help.
#
# The simplest usage of this rule is using the `'+h='` flag on another
# rule. For example:
#
#     make run +h=
#
# Run `'make help ON=<rule>'` to get help on the Makefile rule <rule>.
# Run `'make help ON=<script.py>'` to get help on a Python script.
# Run `'make help ON=web'` to open the web hosted developer docs.
#
# You can use this help interface to figure out how things work
# if you're confused about something. Not everything will be
# documented, but most things will. You can also use other resources
# like Finder itself, and because it probably won't be on Finder,
# Google.
#
# Use the `SYS_PYTHON` variable to tell it which Python to use.
#
# For technical details, see `'make help ON=Makefile.help.py'`.
#
# :variables: ON SYS_PYTHON
ON=
help:
	@$(SYS_PYTHON) Makefile.help.py $(ON) && exit

# Freeze dependencies.
#
# DO NOT use `'pip freeze > requirements.txt'`: it will include either 
# winloop or uvloop in the output, and depending on the next contributor's
# system, it could break. Use this instead.
freeze:
	pip freeze --exclude winloop --exclude uvloop > requirements.txt

.PHONY: deps run finder find4u help docker-build docker-run
endif