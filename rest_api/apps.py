from django.apps import AppConfig
from django.core.signals import request_finished


class RestApiConfig(AppConfig):
    name = "rest_api"

    def ready(self):
        from . import signals