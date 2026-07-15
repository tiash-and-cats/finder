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
import httpx
import asyncio
import traceback
import textwrap
import threading
import time
import platform
import multiprocessing
from servestatic import ServeStaticASGI
from asgiref.wsgi import WsgiToAsgi
import uvicorn

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
logging.captureWarnings(True)

logger = logging.getLogger("make")

class ReverseProxy:
    def __init__(self):
        sys.path.append("finder_proj")
        os.environ["DJANGO_DEBUG"] = "0"
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finder_proj.settings")
        from finder_proj.asgi import application as finder_asgi
        self.finder_asgi = finder_asgi

        self.docs_asgi = ServeStaticASGI(
            self.finder_asgi, root="./docs/build/html/",
            prefix="docs/", index_file=True
        )

        self.status = Status()
        self.status.add_service("Finder")
        self.status.add_service("Find4U")
        self.status.add_service("Documentation")
        self.status.add_service("Status page")
        
        self.status_asgi = create_status_app(self.status)

        self.http = httpx.AsyncClient(
            base_url="http://localhost:3000",
            timeout=httpx.Timeout(
                connect=5.0,    # fail fast if Next.js isn't listening
                read=None,      # disable read timeout (can wait forever)
                write=10.0,     # don't hang on request body upload
                pool=5.0        # don't hang on connection pool acquisition
            )
        )

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

    async def find4u_asgi(self, scope, receive, send):
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        query = scope.get("query_string", b"").decode("latin1")
        url = f"{path}?{query}" if query else path

        # Forward headers from Uvicorn -> Next.js
        headers = {}
        for k, v in scope.get("headers", []):
            header_name = k.decode("latin1").lower()
            headers[header_name] = v.decode("latin1")

        async def req_body_generator():
            while True:
                message = await receive()
                if message["type"] == "http.request":
                    yield message.get("body", b"")
                    if not message.get("more_body", False):
                        break

        try:
            req = self.http.build_request(
                method=method,
                url=url,
                headers=headers,
                content=req_body_generator()
            )
            resp = await self.http.send(req, stream=True)
        except Exception as e:
            # Gracefully handle proxy errors
            traceback.print_exception(e)
            self.status.service_request("Find4U", "502 Bad Gateway")
            err_headers = [(b"content-type", b"text/plain")]
            await send({"type": "http.response.start", "status": 502, "headers": err_headers})
            await send({"type": "http.response.body", "body": f"Oops! Proxy error: {e}".encode("utf-8")})
            return

        response_headers = [
            (k.encode("latin1"), v.encode("latin1")) for k, v in resp.headers.items()
            if k.lower() not in hop_by_hop
        ]

        await send({"type": "http.response.start", "status": resp.status_code, "headers": response_headers})
        async for chunk in resp.aiter_raw():
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        await resp.aclose()

    async def __call__(self, scope, receive, send):
        # Pass non-HTTP operational events directly down to child apps
        if scope["type"] != "http":
            if scope["type"] == "lifespan":
                while True:
                    msg = await receive()
                    if msg["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif msg["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        break
            return

        path = scope.get('path', '')

        # default to Finder
        asgi = self.finder_asgi
        svc = "Finder"

        # if the request targets /find4u, give it to find4u
        if path.startswith("/find4u"):
            asgi = self.find4u_asgi
            svc = "Find4U"

        # if the request targets /docs, redirect to /docs/
        if path == "/docs":
            svc = "Documentation"
            webob_resp = Response()
            webob_resp.status = 301
            webob_resp.location = "/docs/"
            asgi = WsgiToAsgi(webob_resp)

        # if the request targets /docs/, give it to ServeStaticASGI
        if path.startswith("/docs/"):
            asgi = self.docs_asgi
            svc = "Documentation"

        # if the request targets /status, give it to the status Flask app
        if path.startswith("/status"):
            asgi = self.status_asgi
            svc = "Status page"

        async def isend(message):
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                status_line = f"{status_code} Status"
                
                self.status.service_request(svc, status_line)
                
                via_string = f"HTTP/{scope.get('http_version', '1.1')} " \
                             f"Finderservices-Orchestration-{
                               finder_buildinfo.BUILDDATE}-{
                               finder_buildinfo.BUILDBRANCH}-{
                               finder_buildinfo.BUILDCOMMIT}"
                headers = list(message.get("headers", []))
                headers.append((b"via", via_string.encode("latin1")))
                message["headers"] = headers
                
            await send(message)

        await asgi(scope, receive, isend)

    def __exit__(self, *_):
        self.find4u_popen.terminate()
        self.find4u_popen.wait()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.http.aclose())
            else:
                loop.run_until_complete(self.http.aclose())
        except Exception:
            pass

def main():
    logging.getLogger('uvicorn').setLevel(logging.INFO)

    with ReverseProxy() as app:
        port = int(os.environ.get("PORT", 80))

        print()
        print(f"Listening on http://localhost:{port}")
        print(__doc__.split("\n", 2)[-1])
        
        try:
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=port,
                log_config=None,
                loop="auto"
            )
        except KeyboardInterrupt:
            print("Exited")

if __name__ == "__main__":
    main()