#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django konnte nicht importiert werden. Ist die virtuelle Umgebung aktiv?") from exc

    if len(sys.argv) > 1 and sys.argv[1] == "createsuperuser":
        sys.argv[1] = "createemailadmin"

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
