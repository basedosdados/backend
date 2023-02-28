#!/usr/bin/env bash
# start-server.sh
python manage.py makemigrations && python manage.py migrate
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
  (cd /app; python manage.py createsuperuser --no-input)
fi
(cd /app; python manage.py makemigrations && python manage.py migrate)
(cd /app; gunicorn basedosdados_api.wsgi --user www-data --bind 0.0.0.0:8000 --workers 3 --log-level debug --timeout 180) &
nginx -g "daemon off;"
