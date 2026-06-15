#!/bin/sh

echo "Creating migrations..."
python manage.py makemigrations --noinput

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Starting Django..."
python manage.py runserver 0.0.0.0:5181
