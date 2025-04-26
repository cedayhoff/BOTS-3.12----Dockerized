#!/bin/bash
set -e

if [ "$BOTS_DB_ENGINE" != "postgres" ]; then
  if [ ! -f /app/bots/usersys/botsdb ]; then
    echo "No botsdb found, initializing from install/"
    cp /app/bots/install/botsdb /app/bots/usersys/botsdb
    cp /app/bots/install/bots.ini /app/bots/usersys/bots.ini
  fi
else
  echo "Postgres mode detected. Running Django migrations..."
    python3.12 manage.py makemigrations bots
    python3.12 manage.py migrate
    python3.12 manage.py collectstatic --noinput

    echo "Checking if superuser exists..."
    python3.12 manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('bots', 'admin@example.com', 'botsbots')"
fi

exec "$@"