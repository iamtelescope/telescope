from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from telescope.models import APIToken


class Command(BaseCommand):
    help = "Create an API token for a telescope user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Username to create the API token for",
        )
        parser.add_argument(
            "--name",
            required=True,
            help="Name for the API token",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        token_name = options["name"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        api_token = APIToken.create(user=user, name=token_name)
        self.stdout.write(api_token.token)
