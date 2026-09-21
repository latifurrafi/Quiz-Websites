"""Create the admin account if it isn't there yet.

Safe to run on every container start: an existing superuser is left completely
alone, so nobody's password gets reset by a restart.

    python manage.py ensure_admin

Reads DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL. If no password is given
and no superuser exists, one is generated and printed once -- look in the
container logs for it.
"""

import os
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def _random_password(length=20):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Create the admin superuser if one does not already exist."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"))
        parser.add_argument("--email", default=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""))
        parser.add_argument(
            "--password",
            default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", ""),
            help="Leave empty to have one generated and printed.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Admin user "{username}" already exists — leaving it untouched.')
            return

        if User.objects.filter(is_superuser=True).exists():
            existing = ", ".join(
                User.objects.filter(is_superuser=True).values_list("username", flat=True)
            )
            self.stdout.write(f"A superuser already exists ({existing}) — not creating another.")
            return

        password = options["password"]
        generated = False
        if not password:
            password = _random_password()
            generated = True

        User.objects.create_superuser(username=username, email=options["email"], password=password)

        self.stdout.write(self.style.SUCCESS(f'Created admin user "{username}".'))
        if generated:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("  " + "=" * 58))
            self.stdout.write(self.style.WARNING(f"   Generated admin password: {password}"))
            self.stdout.write(self.style.WARNING("   Save it now — this is the only time it is shown."))
            self.stdout.write(self.style.WARNING("  " + "=" * 58))
            self.stdout.write("")
