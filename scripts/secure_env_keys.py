#!/usr/bin/env python3
"""
Utility to secure environment keys in this repo:
- Back up the existing `.env` to `.env.backup` (non-committed)
- Replace `.env` content with placeholders from `.env.example` if present
- Add `.env` to `.gitignore` if it isn't already

Run locally to keep keys safe and avoid accidentally committing secrets.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / '.env'
ENV_BACKUP = ROOT / '.env.backup'
ENV_EXAMPLE = ROOT / '.env.example'
GITIGNORE = ROOT / '.gitignore'


def backup_env():
    if not ENV_FILE.exists():
        print('No .env file found to back up.')
        return False
    shutil.copy2(ENV_FILE, ENV_BACKUP)
    print(f'Backed up .env to {ENV_BACKUP}')
    return True


def write_placeholders_from_example():
    if not ENV_EXAMPLE.exists():
        print('No .env.example found; cannot write placeholders automatically.')
        return False
    content = ENV_EXAMPLE.read_text(encoding='utf-8')
    ENV_FILE.write_text(content, encoding='utf-8')
    print('Wrote placeholders to .env from .env.example')
    return True


def ensure_gitignore_has_env():
    if not GITIGNORE.exists():
        GITIGNORE.write_text('.env\n', encoding='utf-8')
        print('Created .gitignore and added .env')
        return True
    text = GITIGNORE.read_text(encoding='utf-8')
    if '.env' in text:
        print('.env already present in .gitignore')
        return True
    GITIGNORE.write_text(text + '\n.env\n', encoding='utf-8')
    print('Added .env to .gitignore')
    return True


def main():
    print('Securing repository environment keys...')
    if ENV_FILE.exists():
        print('Detected .env file — backing it up and replacing with placeholders.')
        backup_env()
        write_placeholders_from_example()
    else:
        print('No .env file detected; nothing to back up.')
    ensure_gitignore_has_env()
    print('Done. Please review .env.backup for your original keys and delete or store it securely.')


if __name__ == '__main__':
    main()
