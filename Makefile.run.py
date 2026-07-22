"""
This is the script run by the run target in the Makefile.

Please ignore http://localhost:3000, it's the Find4U Next.js 
app. Requests to Find4U are forwarded to it. Using it directly
is not the intended manner (though it will work).

Also do not put this script behind a reverse proxy. It has been
designed to BE the reverse proxy.

This script was not designed to be run directly. Please run it
using make.
"""
import shutil
import signal
import subprocess
import sys
import os
import logging
import urllib3
import traceback
import textwrap
import threading
import logging
import time
import smolurl
from whitenoise import WhiteNoise
#from waitress import serve
from webob import Response
from wsgiref import util

import finder_buildinfo
from status import Status, create_app as create_status_app

NO_COLOR = bool(os.environ.get("NO_COLOR") or not sys.stdout.isatty())

def sfcol(ansi):
    if NO_COLOR:
        return ""
    else:
        return ansi

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: sfcol("\x1b[1;32m"),    # green
        logging.INFO: sfcol("\x1b[1;34m"),     # blue
        logging.WARNING: sfcol("\x1b[1;33m"),  # yellow
        logging.ERROR: sfcol("\x1b[1;31m"),    # red
        logging.CRITICAL: sfcol("\x1b[1;41m"), # red background
    }
    RESET  = sfcol("\x1b[0m")
    BOLD   = sfcol("\x1b[1m")
    DIM    = sfcol("\x1b[2m")

    def formatException(self, exc_info):
        if NO_COLOR:
            r = traceback.format_exception(*exc_info)
        else:
            r = traceback.format_exception(*exc_info, colorize=True)
        return "".join(r).strip()

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        log_line = (
            f"{self.BOLD}{record.name}{self.RESET} - "
            f"{self.DIM}[{self.formatTime(record, '%Y-%m-%d %I:%M:%S %p')}]"
            f"{self.RESET} {color}{record.levelname}:{self.RESET} "
            f"{record.getMessage()}"
        )
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        return log_line

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logging.basicConfig(
    level=logging.getLevelName(os.environ.get("LOGGING_LEVEL", "INFO")), 
    handlers=[handler]
)

logger = logging.getLogger("make")

class ReverseProxy:
    def __init__(self):
        sys.path.append("finder_proj")
        os.environ["DJANGO_DEBUG"] = "0"
        from finder_proj.wsgi import application as finder_wsgi
        self.finder_wsgi = finder_wsgi

        self.docs_wsgi = WhiteNoise(
            finder_wsgi, prefix="docs/", root="./docs/build/html/",
            index_file=True
        )

        self.status = Status()
        self.status.add_service("Finder")
        self.status.add_service("Find4U")
        self.status.add_service("Documentation")
        self.status.add_service("Status page")
        self.status_wsgi = create_status_app(self.status)

        self.http = urllib3.PoolManager(maxsize=20)

    def __enter__(self):
        logger.debug("Starting Next.js")
        
        self.find4u_popen = subprocess.Popen(
            [shutil.which("npx"), "next", "start"],
            cwd="./find4u/web",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PORT": "3000"},
        )

        ready_event = threading.Event()

        def reader():
            for line in self.find4u_popen.stdout:
                line = line.decode("utf-8")
                print(line, end="", flush=True)
                if "Ready" in line:
                    ready_event.set()

        threading.Thread(target=reader, daemon=True).start()

        # Block until we see "Ready"
        ready_event.wait()

        logger.debug("Next.js ready")

        # Set terminal title
        print("\x1b]0;make (Finder) - ReverseProxy\x1b\\", end="", flush=True)
        
        logger.debug("ReverseProxy ready")
        return self

    def find4u_wsgi(self, environ, start_response):
        path   = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET")
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body   = environ["wsgi.input"].read(length) if length > 0 else None

        url = f"http://localhost:3000{path}"

        # Forward headers from Waitress -> Next.js
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                if not util.is_hop_by_hop(header_name.lower()):
                    headers[header_name] = value
        if environ.get("CONTENT_TYPE"):
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if environ.get("CONTENT_LENGTH"):
            headers["Content-Length"] = environ["CONTENT_LENGTH"]

        # Make request with streaming enabled
        try:
            resp = self.http.request(
                method,
                url,
                body=body,
                headers=headers,
                preload_content=False
            )
        except Exception as e:
            # Gracefully handle proxy errors
            traceback.print_exception(e)
            status_line = "502 Bad Gateway"
            response_headers = [("Content-Type", "text/plain")]
            start_response(status_line, response_headers)
            return [f"Oops! Proxy error: {e}".encode("utf-8")]

        status_line = f"{resp.status} {resp.reason}"
        response_headers = filter(
            lambda x: not util.is_hop_by_hop(x[0]), resp.headers.items()
        )

        # Streaming body iterator
        def body_iter():
            for chunk in resp.stream(amt=None):
                if chunk:
                    yield chunk
            resp.release_conn()

        start_response(status_line, response_headers)
        return body_iter()

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')

        # default to Finder
        wsgi = self.finder_wsgi
        svc = "Finder"

        # if the request targets /find4u, give it to find4u
        if path.startswith("/find4u"):
            wsgi = self.find4u_wsgi
            svc = "Find4U"

        # if the request targets /docs, redirect to /docs/
        if path == "/docs":
            wsgi = Response()
            wsgi.status = 301
            wsgi.location = "/docs/"
            svc = "Documentation"

        # if the request targets /docs/, give it to WhiteNoise
        if path.startswith("/docs/"):
            wsgi = self.docs_wsgi
            svc = "Documentation"

        # if the request targets /status, give it to the status Flask app
        if path.startswith("/status"):
            wsgi = self.status_wsgi
            svc = "Status page"

        def start_res(status_line, headerlist):
            log = f"{environ["REQUEST_METHOD"]} {path} {status_line!r}"
            
            code = int(status_line.split(" ", 1)[0])
            
            if code < 400:
                logger.info(log)
            elif code < 500:
                logger.warning(log)
            else:
                logger.error(log)
            
            self.status.service_request(svc, status_line)
            return start_response(status_line, [
                ("via", f"{environ.get("SERVER_PROTOCOL", "HTTP/unknown")} "
                f"Finderservices-Orchestration-{finder_buildinfo.BUILDDATE}-"
                f"{finder_buildinfo.BUILDBRANCH}-{finder_buildinfo.BUILDCOMMIT
                }"), *headerlist
            ])

        return wsgi(environ, start_res)

    def __exit__(self, *_):
        self.find4u_popen.terminate()
        self.find4u_popen.wait()

def main():
    with ReverseProxy() as app:
        port = os.environ.get("PORT", 80)

        print()
        print(f"Listening on http://localhost:{port}")
        print(__doc__.split("\n", 2)[-1])
        try:
            smolurl.http_server(smolurl.wsgi_wrap(app), port=int(port))
        except KeyboardInterrupt:
            print("Exited")

if __name__ == "__main__":
    main()