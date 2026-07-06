#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
