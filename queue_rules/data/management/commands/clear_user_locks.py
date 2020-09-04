from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from data.models import UserLock


def _parse_datetime(string_dt: str) -> datetime:
    return datetime.strptime(string_dt, "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=timezone.utc
    )


class Command(BaseCommand):
    help = "Clear existing user locks."

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--created-before",
            action="store",
            type=_parse_datetime,
            default=None,
            help=(
                "Only delete locks created before this UTC datetime, provided in "
                "the format YYYY-MM-DDTHH:MM:SS (such as 2020-09-04T19:18:09)"
            ),
        )

    def handle(self, *args, **options):
        locks = UserLock.objects.all()

        created_upper_bound = options["created_before"]
        if created_upper_bound is not None:
            locks = locks.filter(created__lt=created_upper_bound)

        num_deleted = locks.delete()[0]
        self.stdout.write(f"Deleted {num_deleted} locks.")
