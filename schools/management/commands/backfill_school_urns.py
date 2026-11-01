"""One-off: copy GIAS URNs onto the existing schools.

Matches on name and postcode, the same way import_laei does.

Usage:
    python manage.py backfill_school_urns --dry-run dev/schools_processed.csv
    python manage.py backfill_school_urns dev/schools_processed.csv
"""

import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from schools.models import School


class Command(BaseCommand):
    help = "Copy GIAS URNs onto existing schools, matching on name and postcode."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen; write nothing.")

    def handle(self, *args, **options):
        with open(options["csv_path"], newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        matched = 0
        problems = []

        with transaction.atomic():
            for row in rows:
                found = School.objects.filter(name=row["name"], postcode=row["postcode"])
                if found.count() != 1:
                    problems.append(f'{row["name"]} ({row["postcode"]}): {found.count()} matches')
                    continue
                school = found.get()
                school.urn = row["urn"]
                school.save(update_fields=["urn"])
                matched += 1

            self.stdout.write(f"matched {matched} of {len(rows)}")
            for p in problems:
                self.stdout.write(self.style.WARNING(f"  not matched: {p}"))

            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run: all changes rolled back."))
                return

        self.stdout.write(self.style.SUCCESS("URNs saved."))