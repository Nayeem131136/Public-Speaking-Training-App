#!/usr/bin/env python
"""Django's command-line tool. Use it to run the server, migrate, test, etc."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Could not import Django. Did you activate the virtual environment "
            "and run: pip install -r requirements.txt ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
