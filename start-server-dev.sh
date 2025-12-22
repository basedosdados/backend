#!/usr/bin/env bash
# start-server-dev.sh

# The compose.yaml file mounts our repository as a volume in the /app folder,
# which overwrites the static files collected during image build.
# So we need to collect the static files again at runtime.
echo "> Collecting static files"
python manage.py collectstatic --no-input --settings=backend.settings.base

echo "> Making migrations"
(cd /app; python manage.py makemigrations)

echo "> Applying migrations"
(cd /app; python manage.py migrate)

echo "> Installing debugpy"
pip install debugpy

echo "> Creating superuser"
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
    (cd /app; python manage.py createsuperuser --no-input)
fi

echo "> Running Huey"
(cd /app; python manage.py run_huey &)

# Start server in development mode with django
echo "> Running server in development mode"
(cd /app; python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000) & nginx -g "daemon off;"
