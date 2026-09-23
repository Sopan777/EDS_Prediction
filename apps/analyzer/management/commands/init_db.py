from django.core.management.base import BaseCommand
from database import init_db

class Command(BaseCommand):
    help = 'Initialize SQLite database schema and tables (analysis_history, reports, presets, users, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Drop and recreate all tables with baseline presets',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        self.stdout.write(self.style.NOTICE(f'Initializing database (reset={reset})...'))
        init_db(reset=reset)
        self.stdout.write(self.style.SUCCESS('Successfully initialized all SQLite database tables.'))
