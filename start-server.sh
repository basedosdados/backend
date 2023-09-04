#!/usr/bin/env bash
# start-server.sh
(cd /app; python manage.py makemigrations)
(cd /app; python manage.py migrate)
if [ "$DJANGO_SETTINGS_MODULE" = "basedosdados_api.settings.dev" ] && [ -f "/app/data.json" ] ; then
  (cd /app; python manage.py runscript -v3 scripts.clean)
  (cd /app; python manage.py loaddata data.json)
  (cd /app; chown -R www-data:www-data /app)
  (cd /app; python manage.py rebuild_index --noinput)
fi
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
  (cd /app; python manage.py createsuperuser --no-input)
fi
(cd /app; gunicorn basedosdados_api.wsgi --user www-data --bind 0.0.0.0:8000 --workers 3 --log-level debug --timeout 180) &
nginx -g "daemon off;"
