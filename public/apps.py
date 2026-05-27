from django.apps import AppConfig


class PublicConfig(AppConfig):
    name = "public"

    def ready(self):
        from public import runtime_i18n
        runtime_i18n.install()