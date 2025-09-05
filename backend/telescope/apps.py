from django.apps import AppConfig
from django.db.models.signals import post_migrate


class TelescopeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "telescope"

    def ready(self):
        import telescope.signals
        post_migrate.connect(self._ensure_site_exists, sender=self)

    def _ensure_site_exists(self, **kwargs):
        from django.contrib.sites.models import Site
        from django.conf import settings

        site_id = settings.SITE_ID
        Site.objects.update_or_create(
            id=site_id,
            defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_NAME},
        )
