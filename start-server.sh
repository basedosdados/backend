#!/usr/bin/env bash
# start-server.sh
echo "> Making migrations"
(cd /app; python manage.py makemigrations)

echo "> Migrating"
(cd /app; python manage.py migrate)

echo "> Creating superuser"
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
    (cd /app; python manage.py createsuperuser --no-input)
fi

echo "> Running Huey"
(cd /app; python manage.py run_huey &)

echo "> Running Gunicorn"
(cd /app; gunicorn backend.wsgi --user www-data --bind 0.0.0.0:8000 --workers 3 --timeout 180) & nginx -g "daemon off;"
