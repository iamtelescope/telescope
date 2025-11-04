import logging
from functools import wraps

from django.core.exceptions import PermissionDenied

from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


logger = logging.getLogger("telescope.auth.decorators")


def global_permission_required(permissions):
    def decorator(view):
        @wraps(view)
        def _wrapped_view(request, *args, **kwargs):
            user_permissions = rbac_manager.get_user_global_permissions(request.user)
            for permission in permissions:
                if permission not in user_permissions:
                    logger.debug(
                        "user %s has no global permission: %s",
                        request.user.username,
                        permission,
                    )
                    raise PermissionDenied("Access Denied")
            return view(request, *args, **kwargs)

        return _wrapped_view

    return decorator
