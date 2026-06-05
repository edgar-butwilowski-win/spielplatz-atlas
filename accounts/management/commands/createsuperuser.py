from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS
from django.utils.text import capfirst

from accounts.utils import generate_internal_username, normalize_email


class Command(BaseCommand):
    help = "Erstellt einen Superadmin mit E-Mail-Adresse als Login. Ein internes username-Feld wird automatisch gesetzt."

    def add_arguments(self, parser):
        parser.add_argument("--email", dest="email", help="E-Mail-Adresse für den Superadmin-Login.")
        parser.add_argument("--first-name", dest="first_name", default="", help="Vorname des Superadmins.")
        parser.add_argument("--last-name", dest="last_name", default="", help="Nachname des Superadmins.")
        parser.add_argument("--noinput", "--no-input", action="store_false", dest="interactive", help="Keine interaktive Eingabe verwenden.")
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS, help="Datenbank, auf der der Benutzer erstellt wird.")

    def handle(self, *args, **options):
        UserModel = get_user_model()
        database = options["database"]
        interactive = options["interactive"]
        email = normalize_email(options.get("email"))
        first_name = (options.get("first_name") or "").strip()
        last_name = (options.get("last_name") or "").strip()

        if interactive:
            email = self._prompt_email(UserModel, database, email)
            if not first_name:
                first_name = input("Vorname (optional): ").strip()
            if not last_name:
                last_name = input("Nachname (optional): ").strip()
            password = self._prompt_password(UserModel, email, first_name, last_name)
        else:
            if not email:
                raise CommandError("--email muss bei --noinput angegeben werden.")
            if UserModel._default_manager.db_manager(database).filter(email__iexact=email).exists():
                raise CommandError("Es gibt bereits einen Benutzer mit dieser E-Mail-Adresse.")
            password = None

        user = UserModel(
            username=generate_internal_username(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=database)
        self.stdout.write(self.style.SUCCESS(f"Superadmin erstellt: {email}"))

    def _prompt_email(self, UserModel, database, initial_email):
        email = initial_email
        while not email:
            email = normalize_email(input("E-Mail-Adresse: "))
            if not email:
                self.stderr.write("Bitte eine E-Mail-Adresse eingeben.")

        while UserModel._default_manager.db_manager(database).filter(email__iexact=email).exists():
            self.stderr.write("Es gibt bereits einen Benutzer mit dieser E-Mail-Adresse.")
            email = normalize_email(input("E-Mail-Adresse: "))

        return email

    def _prompt_password(self, UserModel, email, first_name, last_name):
        verbose_name = capfirst(UserModel._meta.verbose_name)
        fake_user = UserModel(username=generate_internal_username(), email=email, first_name=first_name, last_name=last_name)

        while True:
            password = input("Passwort: ")
            password2 = input("Passwort wiederholen: ")

            if password != password2:
                self.stderr.write("Die beiden Passwörter stimmen nicht überein.")
                continue

            if not password:
                self.stderr.write(f"Das Passwort darf für {verbose_name} nicht leer sein.")
                continue

            try:
                password_validation.validate_password(password, fake_user)
            except Exception as error:
                self.stderr.write("\n".join(getattr(error, "messages", [str(error)])))
                answer = input("Passwort trotzdem verwenden? [y/N]: ").strip().lower()
                if answer not in {"y", "yes", "j", "ja"}:
                    continue

            return password
