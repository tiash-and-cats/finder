default: run

ifeq ($(OS),Windows_NT)
VENV_BIN=./env/Scripts
else
VENV_BIN=./env/bin
endif

PORT=80
SYS_PYTHON=python

ifneq ($(wildcard Makefile.secret),)
include Makefile.secret
# A Makefile.secret must define:
# - export DJANGO_SECRET_KEY = a secret key that Django uses
# - export OPENROUTER_KEY = the OpenRouter API key for Find4U
else
$(warning No Makefile.secret detected. You can choose to create one using the Makefile.secret rule. Or you can make it yourself.)
endif

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

build: deps
	cd finder_proj && .$(VENV_BIN)/python manage.py migrate
	cd finder_proj && .$(VENV_BIN)/python manage.py collectstatic --noinput
	cd find4u/web && npm run build
	source $(VENV_BIN)/activate && cd docs && make

run: deps
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	@# Run the Python runner
	PORT=$(PORT) $(VENV_BIN)/python Makefile.run.py

Makefile.secret: | deps
	$(VENV_BIN)/python build-Makefile.secret.py
	
.PHONY: deps run finder find4u