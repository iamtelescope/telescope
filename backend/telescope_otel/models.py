from django.db import models

from telescope.models import Dashboard


class ProvisionedDashboard(models.Model):
    """Marks a dashboard created by file provisioning; only those are updated by it."""

    dashboard = models.OneToOneField(
        Dashboard, on_delete=models.CASCADE, primary_key=True
    )
