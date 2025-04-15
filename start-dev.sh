#!/usr/bin/env bash
# start-server.sh
echo "> Making migrations"
(cd /app; python manage.py makemigrations)
echo "> Migrating"
(cd /app; python manage.py migrate)
echo "> Installing debugpy"
pip install debugpy
echo "> Creating superuser"
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
(cd /app; python manage.py createsuperuser --no-input)
fi
echo "> Running Huey"
(cd /app; python manage.py run_huey &)
echo "> Running server in development mode"
# Start the server in development mode with django
(cd /app; python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000)
