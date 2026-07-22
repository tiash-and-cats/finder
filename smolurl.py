"""
Tiny module with which you can:
    - send http requests
    - parse URLs
    
smolurl follows redirects; you can change the redirect limit by changing 
smolurl.REDIR_LIMIT (defaults to 5).

smolurl only supports HTTP/1.0 (no https).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import UserDict
from abc import ABC, abstractmethod
import io
import os
import sys
import socket
import traceback
import threading
import posixpath
import json
import re

url_regex = re.compile(r"^(?P<protocol>[a-zA-Z][a-zA-Z0-9+.-]*)(?::\/\/)"
                       r"(?P<hostname>[a-zA-Z0-9.-]+|\[[0-9a-fA-F:.]+\])"
                       r"(?::(?P<port>[0-9]+))?(?:(?P<path>\/[^?\n]*)(?:(?:\?)"
                       r"(?P<query>[^#\n]*)?)?(?:(?:\#)(?P<frag>.*)?)?)?$")

content_type_regex = re.compile(r"^(?P<type>[A-Za-z0-9.+-]+\/[A-Za-z0-9.+-]+)"
                                r"(?:;\s?charset=(?P<charset>[A-Za-z0-9._-]+))"
                                r"?$")

REDIR_LIMIT = 5

class Headers(UserDict):
    def __init__(self, dict_or_iterable=None, **kwargs):
        # Maps lowercase key -> actual key in self.data
        self._lower_map = {}
        super().__init__(dict_or_iterable, **kwargs)

    def __setitem__(self, key, value):
        lower_key = key.lower()
        
        # If the key exists under a different casing, overwrite the original key
        if lower_key in self._lower_map:
            actual_key = self._lower_map[lower_key]
            # Handle casing change if user passes a new key casing
            if actual_key != key:
                del self.data[actual_key]
                self.data[key] = value
                self._lower_map[lower_key] = key
            else:
                self.data[actual_key] = value
        else:
            self.data[key] = value
            self._lower_map[lower_key] = key

    def __getitem__(self, key):
        lower_key = key.lower()
        if lower_key in self._lower_map:
            return self.data[self._lower_map[lower_key]]
        raise KeyError(key)

    def __delitem__(self, key):
        lower_key = key.lower()
        if lower_key in self._lower_map:
            actual_key = self._lower_map.pop(lower_key)
            del self.data[actual_key]
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return key.lower() in self._lower_map

    def __repr__(self):
        return f"Headers({super().__repr__()})"

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

@dataclass
class Request:
    """A dataclass representing a request."""
    url: str
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    data: str = ""
    
@dataclass(frozen=True)
class Response:
    """A dataclass representing a response."""
    status: int
    reason: str
    headers: Headers
    body: bytes
    url: str | None = None

    @property
    def text(self) -> str:
        charset = None
        if "Content-Type" in self.headers:
            match = content_type_regex.match(self.headers["Content-Type"])
            if match and match["charset"]:
                charset = match["charset"]
        return self.body.decode(charset or "latin1", errors="replace")

@dataclass(frozen=True)
class ParsedURL:
    """A dataclass representing a parsed URL."""
    protocol: str
    hostname: str
    port: int | None
    pathname: str | None
    querystr: str | None
    fragment: str | None
    
    def replace(self, **kwargs) -> "ParsedURL":
        """Return a copy of this ParsedURL with some fields replaced."""
        fields = {
            "protocol": self.protocol,
            "hostname": self.hostname,
            "port": self.port,
            "pathname": self.pathname,
            "querystr": self.querystr,
            "fragment": self.fragment,
        }
        fields.update(kwargs)
        return ParsedURL(**fields)

class Processor(ABC):
    """
    A Processor is a class that processes the Response before returning it 
    to the end user.
    """
    
    @abstractmethod
    def process(self, response: Response):
        pass

class CookieJar(Processor):
    """
    A Processor that implements a basic cookie jar.
    """
    def __init__(self):
        self.cookies = {}
        
    def add_cookie(self, key: str, value: str, domain: str, 
                   path: str, *, expires: datetime | None = None):
        """Adds a cookie."""
        x = self.cookies.setdefault(domain, {}).setdefault(path, [])
        x[:] = [c for c in x if not c["key"] == key]
        x.append({
            "key": key,
            "value": value,
            "domain": domain,
            "path": path,
            "expires": expires,
        })
        
    def parse_Set_Cookie(self, Set_Cookie: str, parsed_url: ParsedURL):
        """Parses a Set-Cookie header."""
        parts = [p.strip() for p in Set_Cookie.split(";")]
        key, value = parts[0].split("=", 1)
        options = [p.split("=", 1) if "=" in p else (p, None) for p in parts[1:]]
        path = parsed_url.pathname
        domain = parsed_url.hostname
        expires = None
        for option, value in options:
            match option:
                case "Path":
                    path = value
                case "Domain":
                    domain = value
                case "Expires":
                    try:
                        expires = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                    except:
                        expires = None
                case "Max-Age":
                    try:
                        expires = datetime.now() + timedelta(seconds=int(value))
                    except:
                        expires = None
        self.add_cookie(key, value, domain=domain, path=path, expires=expires)
    
    def get_Cookie(self, parsed_url: ParsedURL):
        """Gets a string for the Cookie header."""
        return "; ".join([
            f"{c["key"]}={c["value"]}" 
            for c in self.cookies[parsed_url.hostname][parsed_url.pathname]
        ])
    
    def refresh(self):
        """Throws out cookies that have become too stale."""
        for domain in self.cookies.values():
            for path in domain.values():
                path[:] = [c for c in path if not (c['expires'] and datetime.now() >= c['expires'])]
    
    def sessionend(self):
        """Deletes session cookies."""
        for domain in self.cookies.values():
            for path in domain.values():
                path[:] = [c for c in path if not c['expires']]
    
    def process(self, res: Response):
        parsed_url = parse_url(res.url)
        if isinstance(res.headers["Set-Cookie"], tuple):
            for Set_Cookie in res.headers["Set-Cookie"]:
                self.parse_Set_Cookie(Set_Cookie, parsed_url)
            return
        self.parse_Set_Cookie(res.headers["Set-Cookie"], parsed_url)

def parse_url(url: str) -> ParsedURL:
    """Parses a URL into individual components and returns a ParsedURL."""
    m = url_regex.match(url)
    if not m:
        raise ValueError(f"Invalid URL: {url}")

    protocol = m.group("protocol")
    hostname = m.group("hostname")
    port = m.group("port")
    path = m.group("path")
    query = m.group("query")
    frag = m.group("frag")

    return ParsedURL(
        protocol=protocol,
        hostname=hostname,
        port=int(port) if port else None,
        pathname=path or None,
        querystr=query or None,
        fragment=frag or None,
    )
    
def unparse_url(parsed_url: ParsedURL) -> str:
    """Joins a parsed URL back into a string."""
    url = f"{parsed_url.protocol}://{parsed_url.hostname}"
    if parsed_url.port: url += f":{parsed_url.port}"
    if parsed_url.pathname: url += parsed_url.pathname
    if parsed_url.querystr: url += f"?{parsed_url.querystr}"
    if parsed_url.fragment: url += f"#{parsed_url.fragment}"
    return url
    
def absolute_url(parent: str | ParsedURL, relative: str) -> ParsedURL:
    """Given a parent URL and a relative URL, returns an absolute URL (as a ParsedURL)."""
    if isinstance(parent, str):
        parent = parse_url(parent)

    # Already absolute
    if "://" in relative:
        return parse_url(relative)

    base = f"{parent.protocol}://{parent.hostname}"
    if parent.port:
        base += f":{parent.port}"

    # Root-relative
    if relative.startswith("/"):
        return parse_url(base + relative)

    # Query-only
    if relative.startswith("?"):
        return parse_url(base + (parent.pathname or "/") + relative)

    # Fragment-only
    if relative.startswith("#"):
        frag_url = base + (parent.pathname or "/")
        if parent.querystr:
            frag_url += "?" + parent.querystr
        frag_url += relative
        return parse_url(frag_url)

    # Otherwise: relative to current path
    path = parent.pathname or "/"
    # Ensure we have a directory base
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    # Normalize with posixpath to handle ../ and ./ segments
    new_path = posixpath.normpath(path + relative)
    return parse_url(base + new_path)

def _parse_raw_hdrs(raw_headers):
    headers_list = [[y.strip() for y in x.split(":", 1)] for x in raw_headers]
    headers = Headers()
    for k, v in headers_list:
        if k in headers:
            if not isinstance(headers[k], tuple):
                headers[k] = (headers[k],)
            headers[k] += (v,)
        else:
            headers[k] = v
    return headers

def urlopen(request_or_url: str | Request, 
            *, follow_redirects: bool = True, processor: Processor = None, 
            _redir=0) -> Response:
    """Creates a request and fetches the response."""
    if isinstance(request_or_url, str):
        request = Request(request_or_url)
    else:
        request = request_or_url
        
    parsed_url = parse_url(request.url)
    
    if parsed_url.protocol.endswith("s"):
        raise RuntimeError("Secure protocols not supported")
    
    port = parsed_url.port or 80
    
    s = socket.socket()
    s.connect((parsed_url.hostname, port))
    
    headers = request.headers.copy()
    headers.setdefault("Host", parsed_url.hostname)
    headers.setdefault("User-Agent", "smolurl")
    headers.setdefault("Connection", "close")
    headers.setdefault("Accept", "*/*")
    if request.data:
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        headers.setdefault("Content-Length", str(len(request.data)))
    
    fullpath = (parsed_url.pathname or "/") + \
               ("?" + parsed_url.querystr if parsed_url.querystr else "")
               
    top_line = f"{request.method} {fullpath} HTTP/1.0"
    header_lines = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
    http_request = f"{top_line}\r\n{header_lines}\r\n\r\n{request.data}"
    s.send(http_request.encode("latin1", errors="replace"))
    
    data = b""
    while True:
        x = s.recv(256)
        if not x: break
        data += x
        
    parts = data.split(b"\r\n\r\n", 1)
    if len(parts) == 2:
        raw_headers, body = parts
    else:
        raw_headers, body = parts[0], b""

    raw_headers = raw_headers.decode("latin1").split("\r\n")
    top = raw_headers.pop(0)
    headers = _parse_raw_hdrs(raw_headers)
    
    _, status, reason = top.split(" ", 2)
    status = int(status)
    
    if follow_redirects and 300 <= status < 400:
        # some people hate standards and send a 3xx without Location
        if "Location" in headers:
            if _redir > REDIR_LIMIT:
                raise RuntimeError("Too many redirects")
                
            return urlopen(
                unparse_url(absolute_url(parsed_url, headers["Location"])),
                _redir=_redir+1
            )
    
    res = Response(
        url=request.url,
        status=status,
        reason=reason,
        headers=headers,
        body=body
    )
    
    if processor:
        processor.process(res)
    
    return res

def wsgi_wrap(app):
    class _WSGIWrapper:
        def __init__(self, app):
            self._app = app
            self._code = 200
            self._reason = "OK"
            self._headers = Headers()
            self._wbuf = io.BytesIO()

        def __call__(self, req):
            it = self._app(self._wsgi_environ(req), self._wsgi_start_response)
            
            for x in it:
                self._wbuf.write(x)
            
            return Response(
                status=self._code,
                reason=self._reason,
                headers=self._headers,
                body=self._wbuf.getvalue()
            )

        def _wsgi_environ(self, req):
            url = parse_url(req.url)
            environ = {
                **os.environ,
                "REQUEST_METHOD": req.method,
                "SCRIPT_NAME": "",
                "PATH_INFO": url.pathname,
                "QUERY_STRING": url.querystr,
                "SERVER_NAME": "localhost",
                "SERVER_PORT": "8080",
                "SERVER_PROTOCOL": "HTTP/1.0",
                "wsgi.version": (1, 0),
                "wsgi.url_scheme": "http",
                "wsgi.input": io.BytesIO(req.data.encode("latin1")),
                "wsgi.errors": sys.stderr,
                "wsgi.multithread": False,
                "wsgi.multiprocess": False,
                "wsgi.run_once": False,
            }
            for k, v in req.headers.items():
                key = "HTTP_" + k.upper().replace("-", "_")
                environ[key] = v if isinstance(v, str) else v[0]
            if "Content-Type" in req.headers:
                environ["CONTENT_TYPE"] = req.headers["Content-Type"]
            if "Content-Length" in req.headers:
                environ["CONTENT_LENGTH"] = req.headers["Content-Length"]
            return environ

        def _wsgi_start_response(self, status, headers, exc_info=None):
            code, reason = status.split(" ", 1)
            self._code = int(code)
            self._reason = reason
            self._headers.update(dict(headers))
            
            return self._wbuf.write

    def handler(req):
        return _WSGIWrapper(app)(req)

    return handler

def http_server(handler, host="127.0.0.1", port=8080, use_threading=True):
    s = socket.socket()
    s.bind((host, port))
    s.listen(5)
    print(f"Serving on {host}:{port}")
    
    def thread(conn):
        try:
            data = b""
            while True:
                chunk = conn.recv(256)
                if not chunk: break
                data += chunk
                if b"\r\n\r\n" in data: break

            parts = data.split(b"\r\n\r\n", 1)
            raw_headers, body_bytes = parts if len(parts) == 2 else (parts[0], b"")
            raw_headers = raw_headers.decode("latin1").split("\r\n")
            top = raw_headers.pop(0)
            headers = _parse_raw_hdrs(raw_headers)

            if "Content-Length" in headers:
                length = int(headers["Content-Length"])
                while len(body_bytes) < length:
                    chunk = conn.recv(length - len(body_bytes))
                    if not chunk: break
                    body_bytes += chunk

            method, path, _ = top.split(" ", 2)
            req = Request(url=f"http://{host}:{port}{path}", method=method,
                          headers=headers, data=body_bytes.decode("latin1", errors="replace"))

            try:
                res = handler(req)
            except Exception as e:
                res = Response(
                    status=500,
                    reason="Internal Server Error",
                    headers=Headers({"Content-Type": "text/plain; charset=utf-8"}),
                    body=b"An error has occurred. Please contact the server administrator."
                )
                traceback.print_exception(e, file=sys.stderr)

            headers = res.headers.copy()
            headers.setdefault("Server", "smolurl")
            headers.setdefault("Connection", "close")
            headers["Content-Length"] = str(len(res.body))

            top_line = f"HTTP/1.0 {res.status} {res.reason}"
            header_lines = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
            http_res = f"{top_line}\r\n{header_lines}\r\n\r\n".encode("latin1") + res.body

            conn.sendall(http_res)
            conn.close()

            print("request:", req.method, req.url, repr(f"{res.status} {res.reason}"))
        except ConnectionResetError:
            pass
    
    while True:
        try:
            conn, addr = s.accept()
            if use_threading:
                threading.Thread(target=thread, args=(conn,)).start()
            else:
                thread(conn)
        except KeyboardInterrupt:
            return