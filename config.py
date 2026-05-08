import os

SECRET_KEY = os.urandom(32)
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

# Connect to local PostgreSQL database
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres@localhost:5432/fyyur'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Disable CSRF for development — add {{ form.hidden_tag() }} to templates to re-enable
WTF_CSRF_ENABLED = False
