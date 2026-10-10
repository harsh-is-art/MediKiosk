# Django Imports

from django.apps import AppConfig


# Medicines Application Confi.

class MedicinesConfig(AppConfig):
    # Default Primary Key Confi.

    default_auto_field = 'django.db.models.BigAutoField'

    # Application Name

    name = 'medicines'