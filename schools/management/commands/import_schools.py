"""Import schools from the pipeline's processed GIAS CSV.

Usage:
    python manage.py import_schools --dry-run data/southwark_lambeth_schools.csv
    python manage.py import_schools data/southwark_lambeth_schools.csv

Reads the output of build_slice.py and creates/updates School rows, keyed
on URN. Keeps all primaries plus any school with pre-reception provision.
Contact details (phone, website) are only set when a school is first
created, so staff edits are never overwritten.
"""

from decimal import Decimal

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from schools.models import School

# LAEI 2022 values added by build_slice.py. The names match the School fields.
LAEI_COLS = [
    "no2_2022",
    "nox_2022",
    "pm25_2022",
    "pm10_mean_2022",
    "pm10_days_2022",
]

REQUIRED_COLS = [
    "URN",
    "EstablishmentName",
    "PhaseOfEducation (name)",
    "TypeOfEstablishment (name)",
    "has_pre_reception_provision",
    "Street",
    "Town",
    "Postcode",
    "LA (name)",
    "NumberOfPupils",
    "SchoolWebsite",
    "TelephoneNum",
    "lat",
    "long",
    "lsoa21cd",
]

REQUIRED_COLS += LAEI_COLS

MIN_ROWS = 140  # 147 expected


class Command(BaseCommand):
    help = "Import schools from the pipeline CSV (keyed on URN)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen; write nothing.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        # Read every column as text; empty cells become "" rather than NaN.
        df = pd.read_csv(path, dtype=str, keep_default_na=False)

        # -- Checks: fail loudly before touching the database. --
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            raise CommandError(f"CSV is missing expected column(s): {missing}")

        is_primary = df["PhaseOfEducation (name)"] == "Primary"
        is_early = df["has_pre_reception_provision"] == "True"
        df = df[is_primary | is_early]

        if len(df) < MIN_ROWS:
            raise CommandError(f"Only {len(df)} schools - below floor of {MIN_ROWS}.")
        if (df["URN"] == "").any():
            raise CommandError("Some schools have no URN.")
        if df["URN"].duplicated().any():
            raise CommandError("Duplicate URNs in CSV.")
        if (df["lat"] == "").any():
            raise CommandError("Some schools have no coordinates.")

        created = updated = 0
        with transaction.atomic():
            for row in df.to_dict("records"):
                
                # LAEI 2022 values: text in the CSV, Decimal in the database.
                laei = {col: decimal_or_none(row[col]) for col in LAEI_COLS}
                
                # Fields that always come from GIAS.
                fields = {
                    "name": row["EstablishmentName"],
                    "address": row["Street"],
                    "city": row["Town"] or "London",
                    "postcode": row["Postcode"],
                    "borough": row["LA (name)"],
                    "latitude": Decimal(row["lat"]),
                    "longitude": Decimal(row["long"]),
                    "lsoa21": row["lsoa21cd"],
                    "school_type": school_type(row),
                    "has_pre_reception_provision": row["has_pre_reception_provision"] == "True",
                    "student_count": int_or_none(row["NumberOfPupils"]),
                    **laei,
                    "laei_data_available": any(v is not None for v in laei.values()),
                }
                _, was_created = School.objects.update_or_create(
                    urn=row["URN"],
                    defaults=fields,
                    # Only for brand new schools: contact details too.
                    create_defaults={
                        **fields,
                        "website": web_address(row["SchoolWebsite"]),
                        "phone": row["TelephoneNum"] or None,
                    },
                )
                created += was_created
                updated += not was_created

            self.stdout.write(f"created {created}, updated {updated}, "
                              f"total in DB {School.objects.count()}")

            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run: all changes rolled back."))
                return

        self.stdout.write(self.style.SUCCESS("Import committed."))


def school_type(row):
    """Translate GIAS phase and type into the model's short codes."""
    phase = row["PhaseOfEducation (name)"]
    kind = row["TypeOfEstablishment (name)"].lower()
    if phase == "Nursery":
        return "nursery"
    if "special" in kind:
        return "special"
    if "independent" in kind:
        return "independent"
    if phase == "All-through":
        return "all_through"
    return "primary"


def int_or_none(value):
    """'19.0' -> 19, '' -> None."""
    return int(float(value)) if value else None


def web_address(value):
    """Add https:// if GIAS left it off, so the link works."""
    if not value:
        return None
    return value if value.startswith("http") else f"https://{value}"

def phone_number(value):
    """GIAS drops the leading 0 from UK numbers: '2077338425' -> '02077338425'."""
    if not value:
        return None
    return value if value.startswith("0") else f"0{value}"

def decimal_or_none(value):
    """'23.95' -> Decimal('23.95'), '' -> None."""
    return Decimal(value).quantize(Decimal("0.01")) if value else None