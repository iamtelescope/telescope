#!/bin/sh
set -e

: "${DJANGO_SECRET_KEY:=dummysecret}"
: "${DJANGO_COLLECTSTATIC:=1}"

if [ "$DJANGO_COLLECTSTATIC" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"