export EXE_NGINX=nginx
export EXE_PYTHON=python

ifneq ($(wildcard Makefile.secret),)

include Makefile.secret
# A Makefile.secret must define:
# - DJANGO_SECRET_KEY = a secret key that Django uses
# - OPENROUTER_KEY = the OpenRouter API key for Find4U

default: deps run

deps:
	@if [ ! -f Makefile.secret ]; then \
		echo "No Makefile.secret found: run make Makefile.secret"; \
		exit 1; \
	fi
	@if [ ! -d env ]; then \
		$(EXE_PYTHON) -m venv env; \
	    source ./env/scripts/activate; \
		pip install -r requirements.txt; \
	fi
	@if [ ! -d find4u/cli/node_modules ]; then \
		cd find4u/cli; \
		npm install; \
	fi
	@if [ ! -d find4u/web/node_modules ]; then \
		cd find4u/web; \
		npm install; \
	fi

finder:
	( source ./env/scripts/activate; \
	  cd finder_proj; \
	  DJANGO_DEBUG=1 $(EXE_PYTHON) manage.py runserver )

find4u:
	@# TODO

run:
	@# Run the Python runner
	DJANGO_DEBUG=0 $(EXE_PYTHON) Makefile.run.py

else # ifeq ($(wildcard myfile.txt),)

$(warning No Makefile.secret detected. You can choose to create one using the Makefile.secret rule. Or you can make it yourself.)

endif

Makefile.secret:
	$(EXE_PYTHON) build-Makefile.secret.py
	
.PHONY: deps run finder find4u