#####################################################
# Makefile containing shortcut commands for project #
#####################################################

# MACOS USERS:
#  Make should be installed with XCode dev tools.
#  If not, run `xcode-select --install` in Terminal to install.

# WINDOWS USERS:
#  1. Install Chocolately package manager: https://chocolatey.org/
#  2. Open Command Prompt in administrator mode
#  3. Run `choco install make`
#  4. Restart all Git Bash/Terminal windows.

.PHONY: create-dev update-dev

create-dev:
	python3 -m venv .venv; \
	. .venv/bin/activate; \
	pip install --upgrade poetry; \
	poetry install; \
	pre-commit install;

update-dev:
	. .venv/bin/activate; \
	poetry update;

.PHONY: docker-clean docker-down docker-force docker-logs docker-start docker-stop docker-up

docker-clean:
	docker-compose down --rmi all --volumes

docker-down:
	docker-compose down --remove-orphans

docker-force:
	docker-compose up --force-recreate

docker-logs:
	docker-compose logs -f

docker-start:
	docker-compose start

docker-stop:
	docker-compose stop

docker-up:
	docker-compose up
