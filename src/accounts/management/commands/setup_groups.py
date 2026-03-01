from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create default permission groups: Admin, Operator, ReadOnly"

    GROUPS = ["Admin", "Operator", "ReadOnly"]

    def handle(self, *args, **options):
        for group_name in self.GROUPS:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group: {group_name}"))
            else:
                self.stdout.write(f"Group already exists: {group_name}")
