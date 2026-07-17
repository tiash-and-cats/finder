# Run by default if no target is given. Synonym of 'make run'.
default: run

ifeq ($(OS),Windows_NT)
VENV_BIN=./env/Scripts
else
VENV_BIN=./env/bin
endif

PORT=80
SYS_PYTHON=python

DOCKER_IMAGE_NAME=finder

LOGGING_LEVEL=INFO

ifneq ($(wildcard Makefile.secret),)
include Makefile.secret
# A Makefile.secret must define:
# - export DJANGO_SECRET_KEY = a secret key that Django uses
# - export OPENROUTER_KEY = the OpenRouter API key for Find4U
else
$(warning No Makefile.secret detected. You can choose to create one using the Makefile.secret rule. Or you can make it yourself.)
endif

# Installs dependencies. 
#
# Use the `SYS_PYTHON` variable to tell it which Python to use.
#
# :variables: SYS_PYTHON
deps:
	@if [ ! -d env ]; then \
		$(SYS_PYTHON) -m venv env; \
		$(VENV_BIN)/pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu; \
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

# Build static files.
build: deps
	cd finder_proj && .$(VENV_BIN)/python manage.py migrate
	cd finder_proj && .$(VENV_BIN)/python manage.py collectstatic --noinput
	cd find4u/web && npm run build
	source $(VENV_BIN)/activate && cd docs && make
	python finder_buildinfo.generate.py

# Start the production server.
#
# (!!) Will fail without Makefile.secret. Please run 'make Makefile.secret' first.
#
# Use `LOGGING_LEVEL` to adjust the logging level. Possible values are `DEBUG`, `INFO`,
# `WARNING`, `ERROR`, and `CRITICAL`. Defaults to `INFO`.
#
# Use `PORT` to change the port the server runs on. Defaults to `80`
#
# For more technical details, see `'make help ON=Makefile.run.py'`.
#
# :variables: LOGGING_LEVEL PORT
run: deps
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	@# Run the Python runner
	LOGGING_LEVEL=$(LOGGING_LEVEL) PORT=$(PORT) $(VENV_BIN)/python Makefile.run.py

# Interactively creates a Makefile.secret file.
Makefile.secret: | deps
	$(VENV_BIN)/python Makefile.secret.generate.py
	
# Build a Docker image. 
#
# Use the `DOCKER_IMAGE_NAME` variable to set the image name (defaults to `finder`).
#
# :variables: DOCKER_IMAGE_NAME
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
help:
	@$(SYS_PYTHON) Makefile.help.py $(ON)

.PHONY: deps run finder find4u help docker-build docker-run