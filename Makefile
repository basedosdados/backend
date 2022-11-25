# Get the executables we're using
POETRY=$(shell which poetry)
PYTHON=$(shell poetry run which python)

# `make install`: installs dependencies
.PHONY: install
install:
	$(POETRY) install

# `make add`: adds a new dependency
ifeq (add,$(firstword $(MAKECMDGOALS)))
	ADD_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
	$(eval $(ADD_ARGS):;@:)
endif

.PHONY: add
add:
	$(POETRY) add $(ADD_ARGS)

# `make remove`: removes a dependency
ifeq (remove,$(firstword $(MAKECMDGOALS)))
	REMOVE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
	$(eval $(REMOVE_ARGS):;@:)
endif

.PHONY: remove
remove:
	$(POETRY) remove $(REMOVE_ARGS)

# `make lint`: runs linters
.PHONY: lint
lint:
	$(POETRY) run lint

# `make migrations`: checks for model changes and generates migrations
.PHONY: migrations
migrations:
	$(PYTHON) manage.py makemigrations

# `make migrate`: applies migrations
.PHONY: migrate
migrate:
	$(PYTHON) manage.py migrate

# `make superuser`: creates a superuser
.PHONY: superuser
superuser:
	$(PYTHON) manage.py createsuperuser

# `make run_local`: runs the server using manage.py
.PHONY: run_local
run_local:
	@echo "Touching the log file to ensure it exists..."
	@touch basedosdados_api/django.log
	@echo "Checking for model changes..."
	@make migrations
	@echo "Applying migrations..."
	@make migrate
	@echo "Running the server at http://0.0.0.0:8080/..."
	$(PYTHON) manage.py runserver 0.0.0.0:8080

# `make run_docker`: runs the server using docker-compose
.PHONY: run_docker
run_docker:
	@docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build --detach

# `make stop_docker`: stops the server using docker-compose
.PHONY: stop_docker
stop_docker:
	@docker compose -f docker-compose.yaml -f docker-compose.dev.yaml down

# `make shell_docker`: runs a shell in the server using docker-compose
.PHONY: shell_docker
shell_docker:
	@docker compose -f docker-compose.yaml -f docker-compose.dev.yaml exec api bash

# `make logs_docker`: shows the logs of the server using docker-compose
.PHONY: logs_docker
logs_docker:
	@docker compose -f docker-compose.yaml -f docker-compose.dev.yaml logs --tail=500 -f

# `make status_docker`: shows the status of the server using docker-compose
.PHONY: status_docker
status_docker:
	@docker compose -f docker-compose.yaml -f docker-compose.dev.yaml ps
