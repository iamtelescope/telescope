#!/bin/sh
set -e

: "${DJANGO_SECRET_KEY:=dummysecret}"
: "${DJANGO_COLLECTSTATIC:=1}"

# "scheduler" runs the alert scheduler instead of the web server; it serves no static files.
if [ "$1" = "scheduler" ]; then
  shift
  exec python manage.py telescope_scheduler "$@"
fi

if [ "$DJANGO_COLLECTSTATIC" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
