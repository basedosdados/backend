#!/usr/bin/env bash
# start-server-dev.sh
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

echo "> Populating PGVector collection"
(cd /app; python manage.py populate_pgvector)

# Start server in development mode with django
echo "> Running server in development mode"
(cd /app; python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000)
