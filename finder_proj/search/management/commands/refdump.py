import os
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Create a reference database backup for contributors.'

    def handle(self, *args, **options):
        # Build an absolute path to prevent breaking if called from different directories
        filename = f"../{time.strftime('%Y-%m-%d')}-ref-db.sqlite3.json"
        
        # Open the file explicitly with utf-8 encoding
        with open(filename, 'w', encoding='utf-8') as f:
            call_command(
                'dumpdata', 
                exclude=['auth', 'contenttypes', 'sessions', 'admin'],
                natural_foreign=True,
                natural_primary=True,
                stdout=f  # Write data straight to the open utf-8 file stream
            )
            
        self.stdout.write(self.style.SUCCESS(f'Successfully exported safe data to {filename}'))