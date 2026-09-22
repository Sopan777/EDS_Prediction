"""
server.py
=========
Compatibility entrypoint for Spectral Lab - MaterialID.
Launches the Django development server on port 8000 (or PORT env var).
"""

import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed in your environment."
        ) from exc

    port = os.environ.get('PORT', '8000')
    sys.argv = ['manage.py', 'runserver', f'0.0.0.0:{port}']
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
