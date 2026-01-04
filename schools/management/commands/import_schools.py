from django.core.management.base import BaseCommand
from schools.models import School
import csv
from decimal import Decimal

class Command(BaseCommand):
    help = 'Load school data from processed CSV into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='schools_processed.csv',
            help='Path to the CSV file',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing schools before loading',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = School.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing schools'))

        file_path = options['file']
        schools_created = 0
        schools_skipped = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Skip if missing required fields
                if not row.get('latitude') or not row.get('longitude'):
                    schools_skipped += 1
                    continue
                
                # Map phase to school_type
                phase = row.get('phase', 'primary').lower()
                school_type = 'nursery' if 'nursery' in phase.lower() else 'primary'
                
                # Get or create school
                school, created = School.objects.get_or_create(
                    name=row['name'],
                    postcode=row.get('postcode', ''),
                    defaults={
                        'address': row.get('street', ''),
                        'city': row.get('town', row.get('local_authority', '')),
                        'latitude': Decimal(row['latitude']),
                        'longitude': Decimal(row['longitude']),
                        'school_type': school_type,
                    }
                )
                
                if created:
                    schools_created += 1
                    self.stdout.write(f'Created: {school.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully loaded {schools_created} schools '
                f'({schools_skipped} skipped due to missing coordinates)'
            )
        )