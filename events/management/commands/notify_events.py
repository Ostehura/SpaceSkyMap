
from django.core.management.base import BaseCommand
from events.notifications import notify


class Command(BaseCommand):
    help = "Sends notifications for upcoming events (next 1–25 hours)."

    def handle(self, *args, **options):
        notify()
        self.stdout.write(self.style.SUCCESS("Notifications processed."))