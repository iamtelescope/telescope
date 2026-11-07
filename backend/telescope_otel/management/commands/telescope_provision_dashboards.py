from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from telescope_otel.provision import provision


class Command(BaseCommand):
    help = (
        "Create or update dashboards from JSON files or directories, matched by slug."
        ' A file holds {"slug", "name", "description", "shared", "data"} or'
        ' {"slug", "template", "sources": {role: source slug}}.'
    )

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", help="JSON files or directories")
        parser.add_argument(
            "--username",
            help="Owner and RBAC identity; defaults to the first superuser",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        if options["username"]:
            user = User.objects.filter(username=options["username"]).first()
        else:
            user = User.objects.filter(is_superuser=True).order_by("id").first()
        if user is None:
            raise CommandError("user not found; pass --username")
        failed = 0
        for path, slug, action in provision(options["paths"], user):
            failed += action.startswith("error")
            self.stdout.write(f"{path}: {slug or '-'} {action}")
        if failed:
            raise CommandError(f"{failed} file(s) failed")
