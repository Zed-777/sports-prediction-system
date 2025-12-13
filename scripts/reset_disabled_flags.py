"""CLI helper to reset disabled flags for host/path or clear all.

Usage:
  python scripts/reset_disabled_flags.py             # show help
  python scripts/reset_disabled_flags.py --list      # list disabled flags
  python scripts/reset_disabled_flags.py --clear-all # clear all disabled flags
  python scripts/reset_disabled_flags.py --host api-football.com --path /v2/players/injuries --clear
"""
from __future__ import annotations
import argparse
from app.utils import state_sync


def main():
    parser = argparse.ArgumentParser(description='Reset or list disabled endpoint flags')
    parser.add_argument('--list', action='store_true', help='List all disabled flags')
    parser.add_argument('--clear-all', action='store_true', help='Clear all disabled flags')
    parser.add_argument('--host', type=str, help='Host for a specific flag')
    parser.add_argument('--path', type=str, help='Path for a specific flag')
    parser.add_argument('--clear', action='store_true', help='Clear a specific host/path flag')
    args = parser.parse_args()

    if args.list:
        flags = state_sync.list_disabled_flags()
        if not flags:
            print('No disabled flags present')
            return
        for h, paths in flags.items():
            print(f'Host: {h}')
            for p, info in paths.items():
                print(f'  {p} -> {info}')
        return

    if args.clear_all:
        state_sync.clear_all_disabled_flags()
        print('Cleared all disabled flags (file or redis)')
        return

    if args.host and args.path and args.clear:
        state_sync.clear_disabled_flag(args.host, args.path)
        print(f'Cleared flag for {args.host} {args.path}')
        return
    parser.print_help()


if __name__ == '__main__':
    main()
