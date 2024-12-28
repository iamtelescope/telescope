from django.apps import AppConfig


class TelescopeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "telescope"

    def ready(self):
        import telescope.signals
