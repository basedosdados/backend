#!/usr/bin/env bash
# start-server.sh
(cd /app; python manage.py makemigrations)
(cd /app; python manage.py migrate)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
  (cd /app; python manage.py createsuperuser --no-input)
fi
(cd /app; python manage.py run_huey &)
(cd /app; gunicorn backend.wsgi --user www-data --bind 0.0.0.0:8000 --workers 3 --timeout 180) & nginx -g "daemon off;"
