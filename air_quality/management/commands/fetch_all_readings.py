"""
Fetch readings from all sensor networks (LAQN and Breathe London).

This combines both fetch commands for easy scheduling via cron.

Usage:
    python manage.py fetch_all_readings
    python manage.py fetch_all_readings --hours=2
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Fetch readings from all sensor networks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Fetch readings from the last N hours (default: 2)'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'Fetching readings from last {hours} hours\n'
                f'{"="*60}\n'
            )
        )
        
        # Fetch LAQN readings
        self.stdout.write('\n[1/2] Fetching LAQN readings...')
        try:
            call_command('fetch_laqn_readings', hours=hours)
            self.stdout.write(self.style.SUCCESS('✓ LAQN fetch complete\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ LAQN fetch failed: {e}\n'))
        
        # Fetch Breathe London readings
        self.stdout.write('[2/2] Fetching Breathe London readings...')
        try:
            call_command('fetch_breathe_readings', hours=hours)
            self.stdout.write(self.style.SUCCESS('✓ Breathe London fetch complete\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Breathe London fetch failed: {e}\n'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'All sensor data fetched successfully!\n'
                f'{"="*60}\n'
            )
        )
