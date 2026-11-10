"""Explicit scoped managed recall CLI. No grant changes, model calls or note writes."""
import argparse
import json
import sys
from managed_memory import read_managed, search_managed


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default messages can echo paths or sensitive input values.
        raise ValueError('MANAGED_RECALL_REFUSED')


def main():
    try:
        parser = SafeParser(description=__doc__)
        parser.add_argument('--grant', required=True)
        parser.add_argument('--grant-sha256', required=True)
        parser.add_argument('--client', required=True)
        commands = parser.add_subparsers(dest='operation', required=True)
        search = commands.add_parser('search')
        search.add_argument('--query', required=True)
        search.add_argument('--limit', type=int, default=4)
        read = commands.add_parser('read')
        read.add_argument('--note-id', required=True)
        read.add_argument('--start-line', type=int, default=1)
        read.add_argument('--line-count', type=int, default=20)
        args = parser.parse_args()
        fixed = (args.grant, args.grant_sha256, args.client)
        if args.operation == 'search':
            result = search_managed(*fixed, args.query, args.limit)
        else:
            result = read_managed(*fixed, args.note_id, args.start_line, args.line_count)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RuntimeError):
        print(json.dumps({'status': 'REFUSED', 'error_code': 'MANAGED_RECALL_REFUSED'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
