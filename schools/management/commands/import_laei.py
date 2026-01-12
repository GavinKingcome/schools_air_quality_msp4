from django.core.management.base import BaseCommand
from schools.models import School
import json
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import LAEI pollution data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='schools_with_laei.json',
            help='Path to the LAEI JSON file',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        self.stdout.write(f'\n📂 Loading pollution data from: {file_path}')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                schools_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File not found: {file_path}'))
            return
        
        updated = 0
        not_found = 0
        no_data = 0
        
        for school_data in schools_data:
            # Try to find school by postcode and name
            try:
                school = School.objects.get(
                    postcode=school_data['postcode'],
                    name=school_data['name']
                )
                
                # Check if pollution data is available
                if not school_data.get('laei_found', False):
                    no_data += 1
                    continue
                
                # Get concentration values
                concentrations = school_data.get('concentrations', {})
                
                # Update pollution fields
                school.no2_2022 = concentrations.get('NO2_2022')
                school.nox_2022 = concentrations.get('NOx_2022')
                school.pm25_2022 = concentrations.get('PM25_2022')
                school.pm10_mean_2022 = concentrations.get('PM10_mean_2022')
                school.pm10_days_2022 = concentrations.get('PM10_days_2022')
                school.laei_data_available = True
                
                school.save()
                updated += 1
                
                self.stdout.write(f'✓ Updated: {school.name}')
                
            except School.DoesNotExist:
                not_found += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ School not found: {school_data["name"]} ({school_data["postcode"]})'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing {school_data["name"]}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Import Complete!'))
        self.stdout.write(f'\n   Schools updated:       {updated}')
        self.stdout.write(f'   Schools not found:     {not_found}')
        self.stdout.write(f'   Schools without data:  {no_data}')
        self.stdout.write(f'   Total in JSON:         {len(schools_data)}')
        self.stdout.write('\n' + '='*70 + '\n')
