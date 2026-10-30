from django.core.management.base import BaseCommand
from core.operations import scan_operations


class Command(BaseCommand):
    help = 'Refresh the staff operations queue. Schedule every 15 minutes; does not send messages or alter business records.'

    def handle(self, *args, **options):
        count = scan_operations()
        self.stdout.write(self.style.SUCCESS(f'Operations scan completed: {count} current issues.'))
