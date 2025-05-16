from typing import Tuple
from django.conf import settings
from django.contrib.auth.models import User

from telescope.models import Source, SavedView
from telescope.constants import VIEW_SCOPE_PERSONAL


def check_user_hit_create_saved_views_limit(
    user: User, source: Source
) -> Tuple[int, str]:
    limit = settings.CONFIG["limits"]["max_saved_views_per_user"]
    if limit > 0:
        saved_views_count = SavedView.objects.filter(
            user=user, scope=VIEW_SCOPE_PERSONAL, source=source
        ).count()
        if saved_views_count >= limit:
            return (
                False,
                f"You have reached the maximum number of saved views ({limit}) for this source",
            )
    return True, ""
