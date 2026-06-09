default: deps run

ifeq ($(OS),Windows_NT)
VENV_BIN=./env/Scripts
else
VENV_BIN=./env/bin
endif

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
	@if [ ! -d find4u/cli/node_modules ] && [ -d find4u/cli ]; then \
		cd find4u/cli; \
		npm install; \
	fi
	@if [ ! -d find4u/web/node_modules ]; then \
		cd find4u/web; \
		npm install; \
	fi

finder:
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	( cd finder_proj; \
	  DJANGO_DEBUG=1 $(VENV_BIN)/python manage.py runserver )

find4u:
	@# TODO

run:
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	@if [ ! -d finder_proj/staticprod ]; then \
		cd finder_proj; \
		.$(VENV_BIN)/python manage.py collectstatic --noinput; \
		cd ..; \
	fi
	@# Run the Python runner
	$(VENV_BIN)/python Makefile.run.py

Makefile.secret: | deps
	$(VENV_BIN)/python build-Makefile.secret.py
	
.PHONY: deps run finder find4u