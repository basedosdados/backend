#!/usr/bin/env bash
# start-server.sh
#(cd /app; python manage.py makemigrations)
#(cd /app; python manage.py migrate)
pip install debugpy

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
  (cd /app; python manage.py createsuperuser --no-input)
fi
(cd /app; python manage.py run_huey &)
# Start the server in development mode with django
(cd /app; python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000)