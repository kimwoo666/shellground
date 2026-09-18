"""Developer CLI for the loopback-only image builder's virtio channel."""
import argparse
import base64
import json
import socket
import sys
from real_vm import GuestChannel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=19473)
    parser.add_argument('--root', action='store_true')
    parser.add_argument('--timeout', type=int, default=30)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    connection = socket.create_connection(('127.0.0.1', args.port), timeout=10)
    connection.settimeout(None)
    channel = GuestChannel(connection)
    try:
        status = channel.request('status', timeout=10)
        if status.get('guest') != 'shellground':
            raise RuntimeError('Not a Shellground guest')
        if not args.command:
            print(json.dumps(status))
            return 0
        result = channel.request('exec', timeout=args.timeout + 5, argv=args.command,
                                 run_timeout=args.timeout, root=args.root,
                                 input=base64.b64encode(sys.stdin.buffer.read()).decode())
        sys.stdout.buffer.write(base64.b64decode(result['out']))
        sys.stderr.buffer.write(base64.b64decode(result['err']))
        return result['code']
    finally:
        channel.close()


if __name__ == '__main__':
    raise SystemExit(main())
