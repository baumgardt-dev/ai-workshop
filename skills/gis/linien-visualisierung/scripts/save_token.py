#!/usr/bin/env python3
"""
Save the Google Maps API token to the OS-native global config location for the
linien-visualisierung skill, so future runs find it automatically without
prompting again.

Token-Ablage (OS-typisch, plattformübergreifend):
    macOS:   ~/Library/Application Support/bc-claude/linien-visualisierung/.env
    Linux:   ~/.config/bc-claude/linien-visualisierung/.env
             (oder $XDG_CONFIG_HOME/bc-claude/...)
    Windows: %APPDATA%\\bc-claude\\linien-visualisierung\\.env

Usage:
    python3 save_token.py <token>
    echo <token> | python3 save_token.py -
    python3 save_token.py --print-path     # nur den Pfad ausgeben

The script picks the OS-native location by default. Override with --path.
"""
import argparse
import os
import sys
from pathlib import Path


def preferred_global_path():
    """Return the OS-native preferred path for the global .env."""
    home = Path.home()
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            base = Path(appdata)
        else:
            base = home / 'AppData' / 'Roaming'
    elif sys.platform == 'darwin':
        base = home / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or (home / '.config'))
    return base / 'bc-claude' / 'linien-visualisierung' / '.env'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('token', nargs='?',
                   help='API token; pass "-" to read from stdin; omit if --print-path')
    p.add_argument('--key', default='TOKEN',
                   help='env var name to write (default: TOKEN)')
    p.add_argument('--path', help='override target path (default: OS-native)')
    p.add_argument('--print-path', action='store_true',
                   help='only print the target path, don\'t write anything')
    args = p.parse_args()

    target = Path(args.path) if args.path else preferred_global_path()

    if args.print_path:
        print(target)
        return

    if not args.token:
        p.error('token required (or use --print-path)')

    if args.token == '-':
        token = sys.stdin.read().strip()
    else:
        token = args.token.strip()
    if not token:
        raise SystemExit('Empty token, refusing to save')

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{args.key}={token}\n", encoding='utf-8')
    try:
        os.chmod(target, 0o600)  # POSIX only; ignored on Windows
    except OSError:
        pass

    print(f"Token saved to: {target}", file=sys.stderr)
    print(target)


if __name__ == '__main__':
    main()
