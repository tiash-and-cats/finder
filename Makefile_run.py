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
import http
import httpx
import traceback
import textwrap
import threading
import math
import time
import platform
import aiofiles
import uvicorn

from webob import Response
from wsgiref import util
from servestatic import ServeStaticASGI
from asgiref.wsgi import WsgiToAsgi

import finder_buildinfo
from status import Status, create_app as create_status_app

import asyncio

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
logging.basicConfig(handlers=[handler])
logging.captureWarnings(True)

logger = logging.getLogger("make")

@(lambda x: x())
def parse_log_level():    
    # parse LOGGING_LEVEL
    log_str = os.environ.get("LOGGING_LEVEL", "")
    
    log_levels = {
        "make": "INFO",
        "uvicorn.error": "INFO",
        "uvicorn.access": "WARNING",
    }
    if "=" in log_str:
        # assume format name=LEVEL, ...
        log_levels.update(dict(
            x.strip().split("=", 1) for x in log_str.split(",")
        ))
    else:
        if log_str == "RESET": 
            # special case: RESET, resets all loggers to defaults
            log_levels = {}
        elif not log_str: pass
        else:
            # legacy format for 'make' only:
            log_levels["make"] = log_str.strip()

    for logger_name, level_val in log_levels.items():
        if logger_name == "*":
            logging.basicConfig(level=level_val)
            continue
            
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.getLevelName(level_val))
    
USE_ASYNCIO_LOOP = bool(os.environ.get("USE_ASYNCIO_LOOP"))

if not USE_ASYNCIO_LOOP:
    try:
        match os.name:
            case "nt":
                import winloop as loop
                logger.debug("Using winloop")
            case "posix":
                import uvloop as loop
                logger.debug("Using uvloop")
            case name:
                import asyncio as loop
                logger.warning(
                    f"Unknown OS {name!r}, using asyncio for safety"
                )
    except ModuleNotFoundError as e:
        import asyncio as loop
        logger.error(f"Couldn't import winloop/uvloop ({e}), using asyncio")
else:
    import asyncio as loop
    logger.info("USE_ASYNCIO_LOOP is set, forcing asyncio")

SSL_KEYFILE = os.environ.get("SSL_KEYFILE")
SSL_CERTFILE = os.environ.get("SSL_CERTFILE")

class ReverseProxy:
    """
    The main class in this file. This class is an async context manager that
    acts as an ASGI app that serves Finder Services.
    """

    CATASTROPHIC_ERROR_PAGE = textwrap.dedent("""
        <!doctype html>
        <html>
        <head>
        <meta 
            name="viewport" 
            content="width=device-width, initial-scale=1.0">
        <style>
        .tab-panel {
          display: none;
        }

        .tabs-container:has(#tab1:checked) #content1,
        .tabs-container:has(#tab2:checked) #content2 {
          display: block;
        }
        </style>
        </head>
        <body>

        <h1>
            An error of CATASTROPHIC proportions has occurred.
        </h1>

        <p>No cat pictures this time, sadly.</p>

        <h2>What happened?</h2>
        <p>
            It's not easy to say, but something definitely went
            wrong somewhere.
        </p>
        <p><strong>Technical Jargon!</strong>
            As you are seeing this screen, the error was not at
            the framework layer, but rather at the reverse
            proxy layer.
        </p>

        <h2>
            I knew I shouldn't have pressed the big red button...
            What do I do?
        </h2>
        <p>
            You can report this bug
            <a href="https://github.com/tiash-and-cats/finder/issues/new">
                here</a>
            if you have a GitHub account. If you don't, then sorry to
            say, but you can't. Hopefully we'll have anonymous bug
            reports someday. Anyway, until then, you'll have to just
            go about your day and pretend nothing happened.
        </p>

        <h2>I crave more technical information...</h2>
        <p>
            If you select the Visualization radio button below,
            you will see a traceback visualization generated
            by <code>cgitb</code>. If you select "Copy-paste view", you
            get a format suitable to copy and paste in your
            bug report. You can see the traceback to figure
            out what happened or you can include it in your
            bug report.
        </p>

        <div class="tabs-container">
          <p class="tabs-nav">
            <label class="tab-label">
              <input type="radio" id="tab1" name="tab-group" checked>
              Visualization
            </label>
            <label class="tab-label">
              <input type="radio" id="tab2" name="tab-group">
              Copy-paste view
            </label>
          </p>

          <div class="tabs-content">
            <div id="content1" class="tab-panel">
              <p><strong><u>WARNING!</u></strong>
                THIS VISUALIZATION MAY CONTAIN
                PERSONAL INFORMATION SUCH AS COOKIES. AS SUCH, NEVER
                SCREENSHOT IT WITHOUT CENSORING SENSITIVE INFO. IN BUG
                REPORTS, COPY THE TEXT IN THE COPY-PASTE VIEW.
              </p>
              %(cgitb)s
            </div>
            <div id="content2" class="tab-panel">
              <pre>%(raw)s</pre>
            </div>
          </div>
        </div>

        </body>
        </html>
    """).strip()

    def __init__(self):
        sys.path.append("finder_proj")
        os.environ["DJANGO_DEBUG"] = "0"
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finder_proj.settings")
        from finder_proj.asgi import application as finder_asgi
        self.finder_asgi = finder_asgi

        async def docs_fallback(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/html")]
            })
            await send({
                "type": "http.response.body",
                "body": self.docs_notfound_html,
                "more_body": False
            })

        self.docs_asgi = ServeStaticASGI(
            docs_fallback, root="./docs/build/html/",
            prefix="docs/", index_file=True
        )

        with open("docs/build/html/404.html", "rb") as f:
            self.docs_notfound_html = f.read()

        self.status = Status()
        self.status.add_service("Finder")
        self.status.add_service("Find4U")
        self.status.add_service("Documentation")
        self.status.add_service("Status page")
        self.status.add_service("Uncategorized")

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

        self.find4u_logger = logging.getLogger("make.nextjs")

    async def __aenter__(self):
        """
        Launches the Next.js frontend process for Find4U and waits until it is
        ready.

        It starts the Next.js server as a subprocess, monitors its output
        until it looks ready, and then returns the proxy instance.

        This is a special method invoked when entering an async context manager.
        For details, see:
            https://docs.python.org/3/reference/datamodel.html#object.__aenter__
        """
        logger.debug("Starting Next.js")

        self.find4u_popen = await asyncio.create_subprocess_exec(
            shutil.which("npx"), "next", "start",
            cwd="./find4u/web",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PORT": "3000"},
        )

        ready_event = asyncio.Event()

        async def reader(stream, cb):
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode("utf-8")
                cb(line_str.rstrip())
                if "Ready" in line_str:
                    ready_event.set()

        asyncio.create_task(reader(
            self.find4u_popen.stdout, self.find4u_logger.info))
        asyncio.create_task(reader(
            self.find4u_popen.stderr, self.find4u_logger.error))

        # Clean async wait boundary replacing threading event blockades
        await ready_event.wait()

        logger.debug("Next.js ready")

        # Set terminal title
        print(f"\x1b]0;make run (Finder ReverseProxy; {
              finder_buildinfo.BUILDCOMMIT})\x1b\\", end="", flush=True)

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
            err_headers = [(b"content-type", b"text/plain")]
            await send({
                "type": "http.response.start",
                "status": 502,
                "headers": err_headers
            })
            await send({
                "type": "http.response.body",
                "body": f"Oops! Proxy error: {e}".encode("utf-8")
            })
            return

        response_headers = [
            (k.encode("latin1"), v.encode("latin1")) for k, v in \
            resp.headers.items()
        ]

        await send({
            "type": "http.response.start",
            "status": resp.status_code,
            "headers": response_headers
        })

        async for chunk in resp.aiter_raw():
            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True
            })

        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False
        })

        await resp.aclose()

    async def main_asgi(self, scope, receive, send):
        """
        This is the main ASGI app.

        Incoming HTTP requests are routed to the appropriate service based
        on their path:
            - requests beginning with /find4u are proxied to the Find4U
              Next.js frontend,
            - those under /docs are served from the documentation build,
            - and those under /status are handled by the status monitoring
              app.

        All other requests default to the Finder Django backend.
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
            wsgi = Response()
            wsgi.status = 301
            wsgi.location = "/docs/"
            asgi = WsgiToAsgi(wsgi)
            svc = "Documentation"

        # if the request targets /docs/, give it to ServeStaticASGI
        if path.startswith("/docs/"):
            asgi = self.docs_asgi
            svc = "Documentation"

        # if the request targets /status, give it to the status Flask app
        if path.startswith("/status"):
            asgi = self.status_asgi
            svc = "Status page"

        if path == "/worse500": raise ValueError("oh no...")

        if "finder.statuspage_set_service" in scope["extensions"]:
            await send({
                "type": "finder.statuspage_set_service",
                "name": svc
            })
        await asgi(scope, receive, send)

    async def error_asgi(self, scope, receive, send, e):
        """
        Called by __call__ to handle exceptions raised by main_asgi.
        
        It uses cgitb (from legacy-cgi) to render a nicely formatted
        HTML stack trace and traceback.format_exception to render
        a stack trace to copy-paste.
        """
        import cgitb
        
        if "finder.statuspage_set_service" in scope["extensions"]:
            await send({
                "type": "finder.set_exception",
                "exc": e
            })
        
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"Content-Type", b"text/html")]
        })
        await send({
            "type": "http.response.body",
            "body": (ReverseProxy.CATASTROPHIC_ERROR_PAGE % {
                "cgitb": cgitb.html((type(e), e, e.__traceback__)),
                "raw": "".join(traceback.format_exception(e))
            }).encode("utf-8"),
            "more_body": False
        })

    async def __call__(self, scope, receive, send):
        """
        This special method makes the class itself callable as an ASGI app.
        For more information, see:
            https://docs.python.org/3/reference/datamodel.html#object.__call__

        This calls main_asgi but with a custom send function. It
        annotates each response with a custom Via header containing
        build metadata before being returned to the client, while
        also logging each request to the console and to a Status
        object (self.status) which is connected to the status page.
        
        If main_asgi raises an error, it calls error_asgi to handle it.
        
        It also intercepts messages with types indicating a "finder"
        protocol. Currently two message types in that protocol are
        supported:
        
            finder.statuspage_set_service
                This sets the service name used when reporting to the
                status app to the value of the "name" key.
            
            finder.set_exception
                This is sent by error_asgi. It sets an exception (the
                value of the "exc" key) to be logged to the console.
        
        These are of course listed in scope["extensions"].
        """

        scope.setdefault("extensions", {}).update({
            "finder.statuspage_set_service": {},
            "finder.set_exception": {},
        })

        svc = "Uncategorized"
        exc = None
        status_code = None
        status_line = None

        async def isend(message):
            if scope["type"] != "http": return await send(message)
            
            nonlocal svc, exc, status_code, status_line

            if message["type"].startswith("finder."):
                match message["type"]:
                    case "finder.statuspage_set_service":
                        svc = message["name"]
                    case "finder.set_exception":
                        exc = message["exc"]
                return

            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                status_line = f"{status_code} {
                              http.HTTPStatus(status_code).phrase}"

                via_string = f"HTTP/{scope.get('http_version', '1.1')} " \
                             f"Finderservices-Orchestration-{
                               finder_buildinfo.BUILDDATE}-{
                               finder_buildinfo.BUILDBRANCH}-{
                               finder_buildinfo.BUILDCOMMIT}"
                headers = list(message.get("headers", []))
                headers.append((b"via", via_string.encode("latin1")))
                message["headers"] = headers

            await send(message)

        start_time = time.perf_counter()
        try:
            await self.main_asgi(scope, receive, isend)
        except Exception as e:
            await self.error_asgi(scope, receive, isend, e)
        time_taken = time.perf_counter() - start_time 
        time_taken_ms = time_taken * 1000
        
        if status_line is None:
            status_code = 500
            status_line = "500 Internal Server Error"

        self.status.service_request(svc, status_line)
        
        log = f"{scope["method"]} {scope.get('path', '')} {
              status_line!r} in {time_taken_ms:.4f}ms"

        if status_code < 400:
            logger.info(log, exc_info=exc)
        elif status_code < 500:
            logger.warning(log, exc_info=exc)
        else:
            logger.error(log, exc_info=exc)

    async def __aexit__(self, *_):
        """
        Cleans up resources when leaving the ReverseProxy context.

        This is the companion to __aenter__, called when leaving the async
        context manager.
        For more information, see:
            https://docs.python.org/3/reference/datamodel.html
            #object.__aexit__

        This method terminates the Next.js subprocess that was started in
        __aenter__, then closes the httpx client used for proxying requests.
        """
        try:
            self.find4u_popen.terminate()
        except ProcessLookupError:
            logger.debug("Find4U seems to be already terminated, ignoring")
        await self.find4u_popen.wait()
        await self.http.aclose()

async def main():
    """Entry point."""
    logging.getLogger('uvicorn').setLevel(logging.INFO)

    async with ReverseProxy() as app:
        proto = {True: "https", False: "http"}[
            bool(SSL_KEYFILE and SSL_CERTFILE)
        ]
        
        port = int(
            os.environ.get("PORT") or {"http": "80", "https": "443"}[proto]
        )

        print()
        print(f"Listening on {proto}://localhost:{port}")
        print(__doc__.split("\n", 2)[-1])

        config = uvicorn.Config(
            app,
            host="127.0.0.1" if platform.system() == "Windows" else "0.0.0.0",
            port=port,
            log_config=None,
            ssl_keyfile=SSL_KEYFILE,
            ssl_certfile=SSL_CERTFILE,
        )
        server = uvicorn.Server(config)

        await server.serve()

if __name__ == "__main__":
    try:
        loop.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted: Gracefully exiting...")