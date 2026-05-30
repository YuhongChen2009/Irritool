"""
Launch IrriTool and close the browser tab when the server stops.

Usage:  python run.py
Stop:   Ctrl+C  (the tab closes automatically)
"""
import subprocess
import sys
import threading
import time
import webbrowser

PORT = 8501
URL = f"http://localhost:{PORT}"


def _open_browser():
    # Wait for Streamlit to be ready before opening the tab.
    time.sleep(2)
    webbrowser.open(URL)


def main():
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT),
         "--server.headless", "true"],
    )

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        # Send a JS close command via a tiny HTTP response on the same port.
        # Since the server is already stopping, inject the close via a
        # temporary page served to the already-open tab.
        _close_tab()


def _close_tab():
    """Serve a one-shot page that calls window.close() to the open browser tab."""
    import http.server
    import socketserver

    html = b"<script>window.close();</script><p>Server stopped. You may close this tab.</p>"

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, *args):
            pass  # suppress access log

    # Give the browser a moment to notice the Streamlit server is gone,
    # then serve the close page on the same port.
    time.sleep(0.5)
    try:
        with socketserver.TCPServer(("", PORT), _Handler) as httpd:
            httpd.timeout = 3
            # Navigate the existing tab to the close page.
            webbrowser.open(URL)
            httpd.handle_request()
    except OSError:
        pass  # port still in use; skip close attempt


if __name__ == "__main__":
    main()
