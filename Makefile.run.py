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
    """
    Wraps ANSI escapes so that they respect NO_COLOR and checks if sys.stdout
    is a TTY. If NO_COLOR is not defined and sys.stdout is a TTY, then returns
    the escape sequence it was passed. Otherwise, returns an empty string.
    """
    if NO_COLOR:
        return ""
    else:
        return ansi

class ColorFormatter(logging.Formatter):
    """
    Adds nice colors to logging.
    """
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
        """
        Format an exception. If NO_COLOR is False, returns a colorized
        traceback, otherwise a non-colorized one.
        """
        if NO_COLOR:
            r = traceback.format_exception(*exc_info)
        else:
            r = traceback.format_exception(*exc_info, colorize=True)
        return "".join(r).strip()

    def format(self, record):
        """
        Format a record. The format is hardcoded here.
        """
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
    """
    The main class in this file. This class is an async context manager that 
    acts as an ASGI app that serves Finder Services.
    """
    
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

    async def __aenter__(self):
        """
        Launches the Next.js frontend process for Find4U and waits until it is 
        ready.
        
        It starts the Next.js server as a subprocess, monitors its output 
        until it looks ready, and then returns the proxy instance.
        
        This is a special method invoked when entering a context manager.
        For details, see:
            https://docs.python.org/3/reference/datamodel.html#object.__enter__
        """
        logger.debug("Starting Next.js")
        
        self.find4u_popen = await asyncio.create_subprocess_exec(
            shutil.which("npx"), "next", "start",
            cwd="./find4u/web",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PORT": "3000"},
        )

        ready_event = asyncio.Event()

        async def reader():
            while True:
                line = await self.find4u_popen.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8")
                print(line_str, end="", flush=True)
                if "Ready" in line_str:
                    ready_event.set()

        asyncio.create_task(reader())

        # Clean async wait boundary replacing threading event blockades
        await ready_event.wait()

        logger.debug("Next.js ready")

        # Set terminal title
        print("\x1b]0;make (Finder) - ReverseProxy\x1b\\", end="", flush=True)
        
        logger.debug("ReverseProxy ready")
        return self

    async def find4u_asgi(self, scope, receive, send):
        """
        ASGI application that proxies requests to the Find4U Next.js frontend.

        This method accepts the standard ASGI parameters: a connection scope
        dictionary with path, method, headers, and query string; a coroutine
        to receive incoming HTTP request events; and a coroutine to send
        responses back to the client. 
        
        It forwards the request headers and body to the Next.js server, 
        streams the response back to the caller, and handles proxy errors 
        gracefully by returning a 502 Bad Gateway response.
        
        You usually don't need to call this directly. Just call the
        ReverseProxy instance instead. It will automatically use this
        method if needed.
        """
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
            (k.encode("latin1"), v.encode("latin1")) for k, v in \
            resp.headers.items()
        ]

        await send({"type": "http.response.start", "status": resp.status_code, "headers": response_headers})
        async for chunk in resp.aiter_raw():
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        await resp.aclose()

    async def __call__(self, scope, receive, send):
        """
        This special method makes the class itself callable as an ASGI app. 
        For more information, see:
            https://docs.python.org/3/reference/datamodel.html#object.__call__

        Incoming HTTP requests are routed to the appropriate service based
        on their path: 
            - requests beginning with /find4u are proxied to the Find4U 
              Next.js frontend, 
            - those under /docs are served from the documentation build, 
            - and those under /status are handled by the status monitoring 
              app.
        
        All other requests default to the Finder Django backend. Each 
        response is annotated with a custom Via header containing build
        metadata before being returned to the client.
        """
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

    async def __aexit__(self, *_):
        """
        Cleans up resources when leaving the ReverseProxy context.
        
        This is the companion to __enter__, called when leaving the context 
        manager.
        For more information, see:
            https://docs.python.org/3/reference/datamodel.html
            #object.__exit__

        This method terminates the Next.js subprocess that was started in
        __enter__, then closes the httpx client used for proxying requests.
        """
        try:
            self.find4u_popen.terminate()
        except ProcessLookupError:
            print("Find4U seems to be already terminated, ignoring")
        await self.find4u_popen.wait()
        await self.http.aclose()

async def main():
    """Entry point."""
    logging.getLogger('uvicorn').setLevel(logging.INFO)

    async with ReverseProxy() as app:
        port = int(os.environ.get("PORT", 80))

        print()
        print(f"Listening on http://localhost:{port}")
        print(__doc__.split("\n", 2)[-1])
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1" if platform.system() == "Windows" else "0.0.0.0",
            port=port,
            log_config=None,
            loop="auto"
        )
        server = uvicorn.Server(config)
        
        await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Gracefully exiting...")