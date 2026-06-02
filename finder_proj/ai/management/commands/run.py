from django.core.management.commands.runserver import Command as RunServer

class Command(RunServer):
    def check(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("⚠️ Skipping system checks!"))

    def check_migrations(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("⚠️ Skipping migration checks!"))