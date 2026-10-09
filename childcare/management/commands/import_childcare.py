"""Import childcare settings from the pipeline's processed CSV.

Usage:
    python manage.py import_childcare path/to/southwark_lambeth_childcare.csv
    python manage.py import_childcare --dry-run path/to/...csv

Reads the output of build_slice.py (schools-pollution-analysis repo) and
creates/updates ChildcareSetting rows, keyed on the provider URN.
Re-running with the same file is safe: existing rows update, nothing duplicates.
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from childcare.models import ChildcareSetting

# NOTE: "Provider URN" is the establishment's own id, published for ALL
# providers. Do not confuse with "Registered person URN", which Ofsted
# withholds for home-based providers.
REQUIRED_COLS = [
    "Provider URN",
    "Provider name",
    "Provider type",
    "Individual register combinations",
    "Places",
    "Postcode",
    "Local authority",
    "lat",
    "long",
    "east1m",
    "north1m",
    "lsoa21cd",
]

PROVIDER_TYPE_MAP = {
    "Childcare on non-domestic premises": "non_domestic",
    "Childminder": "childminder",
    "Childcare on domestic premises": "domestic",
}

MIN_ROWS = 550  # same floor philosophy as the pipeline


class Command(BaseCommand):
    help = "Import childcare settings from the pipeline CSV (keyed on Provider URN)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen; write nothing.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        df = pd.read_csv(path, dtype={"Provider URN": str}, low_memory=False)

        # -- Checks, pipeline-style: fail loudly before touching the DB. --
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            raise CommandError(f"CSV is missing expected column(s): {missing}")
        if len(df) < MIN_ROWS:
            raise CommandError(f"Only {len(df)} rows - below floor of {MIN_ROWS}.")
        unknown_types = set(df["Provider type"].dropna()) - set(PROVIDER_TYPE_MAP)
        if unknown_types:
            raise CommandError(f"Unmapped provider type(s): {unknown_types}")
        if df["Provider URN"].isna().any():
            raise CommandError("Some rows have no Provider URN.")
        if df["Provider URN"].duplicated().any():
            raise CommandError("Duplicate Provider URNs in CSV.")

        created = updated = 0
        with transaction.atomic():
            for row in df.itertuples(index=False):
                _, was_created = ChildcareSetting.objects.update_or_create(
                    urn=getval(row, df, "Provider URN"),
                    defaults={
                        "name": none_to_blank(row, df, "Provider name"),
                        "provider_type": PROVIDER_TYPE_MAP[getval(row, df, "Provider type")],
                        "register_combination": none_to_blank(row, df, "Individual register combinations"),
                        "places": int_or_none(getval(row, df, "Places")),
                        "postcode": none_to_blank(row, df, "Postcode"),
                        "borough": getval(row, df, "Local authority"),
                        "latitude": float_or_none(getval(row, df, "lat")),
                        "longitude": float_or_none(getval(row, df, "long")),
                        "easting": int_or_none(getval(row, df, "east1m")),
                        "northing": int_or_none(getval(row, df, "north1m")),
                        "lsoa21": none_to_blank(row, df, "lsoa21cd"),
                    },
                )
                created += was_created
                updated += not was_created

            self.stdout.write(f"created {created}, updated {updated}, "
                              f"total in DB {ChildcareSetting.objects.count()}")

            if options["dry_run"]:
                raise CommandError("Dry run requested - rolling back all changes.")

        self.stdout.write(self.style.SUCCESS("Import committed."))


def getval(row, df, col):
    return row[df.columns.get_loc(col)]

def float_or_none(v):
    return None if pd.isna(v) else float(v)

def int_or_none(v):
    return None if pd.isna(v) else int(v)

def none_to_blank(row, df, col):
    v = getval(row, df, col)
    return "" if pd.isna(v) else str(v)