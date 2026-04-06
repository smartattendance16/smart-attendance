"""
run.py — SmartAttend Launcher
Starts the Flask server and optionally opens a public tunnel.

Usage:
    python run.py                  # Local only (http://0.0.0.0:5000)
    python run.py --tunnel         # Public URL via localtunnel
    python run.py --tunnel --name smartattend16
"""

import os
import sys
import subprocess
import webbrowser
import argparse
import time

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, SRC_DIR)

def main():
    parser = argparse.ArgumentParser(description='SmartAttend Launcher')
    parser.add_argument('--tunnel', action='store_true',
                        help='Create a public URL via localtunnel')
    parser.add_argument('--name', default='smartattend16',
                        help='Custom subdomain for the tunnel (default: smartattend16)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to run on (default: 5000)')
    parser.add_argument('--no-browser', action='store_true',
                        help='Do not open browser automatically')
    args = parser.parse_args()

    tunnel_proc = None

    try:
        # Start tunnel if requested
        if args.tunnel:
            print(f'\n[TUNNEL] Starting localtunnel with subdomain: {args.name}')
            tunnel_proc = subprocess.Popen(
                ['npx.cmd', '-y', 'localtunnel', '--port', str(args.port),
                 '--subdomain', args.name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            # Wait a moment for the URL
            time.sleep(5)
            line = tunnel_proc.stdout.readline().strip()
            if line:
                print(f'[TUNNEL] {line}')
                print(f'[TUNNEL] Share this URL with students for self-registration!')
            print()

        # Start Flask
        print(f'[SERVER] Starting SmartAttend on port {args.port}...')
        if not args.no_browser:
            url = f'http://localhost:{args.port}'
            print(f'[SERVER] Opening {url} in browser...')
            webbrowser.open(url)

        # Import and run
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        from app import app, init_db
        init_db()
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)

    except KeyboardInterrupt:
        print('\n[SERVER] Shutting down...')
    finally:
        if tunnel_proc:
            tunnel_proc.terminate()
            print('[TUNNEL] Tunnel closed.')


if __name__ == '__main__':
    main()
