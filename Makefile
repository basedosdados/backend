# Get the executables we're using
POETRY=$(shell which poetry)
PYTHON=$(shell poetry run which python)

# `make install`: installs dependencies
.PHONY: install
install:
	$(POETRY) install

# `make install`: installs pre-commit
.PHONY: install_precommit
install_precommit:
	$(POETRY) run pre-commit install --install-hooks

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

# `make migrations_docker`: checks for model changes and generates migrations using docker-compose
.PHONY: migrations_docker
migrations_docker:
	docker-compose exec api python manage.py makemigrations

# `make migrate`: applies migrations
.PHONY: migrate
migrate:
	$(PYTHON) manage.py migrate

# `make migrate_docker`: applies migrations using docker-compose
.PHONY: migrate_docker
migrate_docker:
	docker-compose exec api python manage.py migrate

# `make loadfixture`: load fixtures
.PHONY: loadfixture
loadfixture:
	$(PYTHON) manage.py loadfixture fixture.json

# `make loadfixture_docker`: load fixtures using docker-compose
.PHONY: loadfixture_docker
loadfixture_docker:
	docker-compose exec api python manage.py loadfixture /app/fixture.json

# `make superuser`: creates a superuser
.PHONY: superuser
superuser:
	$(PYTHON) manage.py createsuperuser

# `make superuser_docker`: creates a superuser using docker-compose
.PHONY: superuser_docker
superuser_docker:
	docker-compose exec api python manage.py createsuperuser

# `make run_local`: runs the server using manage.py
.PHONY: run_local
run_local:
	@echo "Touching the log file to ensure it exists..."
	@touch backend/django.log
	@echo "Checking for model changes..."
	@make migrations
	@echo "Applying migrations..."
	@make migrate
	@echo "Running the server at http://0.0.0.0:8080/..."
	$(PYTHON) manage.py runserver 0.0.0.0:8080

# `make run_docker`: runs the server using docker-compose
.PHONY: run_docker
run_docker:
	docker-compose up --build --force-recreate --detach

# `make stop_docker`: stops the server using docker-compose
.PHONY: stop_docker
stop_docker:
	docker-compose stop

# `make clean_docker`: removes the server using docker-compose and delete all volumes
.PHONY: clean_docker
clean_docker:
	docker-compose down --volumes

# `make shell_docker`: runs a shell in the server using docker-compose
.PHONY: shell_docker
shell_docker:
	docker-compose exec api bash

# `make logs_docker`: shows the logs of the server using docker-compose
.PHONY: logs_docker
logs_docker:
	docker-compose logs --tail=500 -f

# `make status_docker`: shows the status of the server using docker-compose
.PHONY: status_docker
status_docker:
	docker-compose ps

# `make sync_stripe`: sync stripe models
.PHONY: sync_stripe
sync_stripe:
	python manage.py djstripe_sync_models
