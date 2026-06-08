import shutil
import signal
import subprocess
import sys
import os
import logging
import urllib3
import traceback
from waitress import serve

def reverse_proxy():
    sys.path.append("finder_proj")
    from finder_proj.wsgi import application as finder_wsgi
    
    find4u_popen = subprocess.Popen([shutil.which("npx"), "next", "start"], cwd="./find4u/web", env={**os.environ})
    HOP_BY_HOP = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "upgrade",
        "transfer-encoding",  # Waitress can't handle chunked
    }
    http = urllib3.PoolManager(maxsize=20)

    def find4u_wsgi(environ, start_response):
        path   = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET")
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body   = environ["wsgi.input"].read(length) if length > 0 else None

        url = f"http://localhost:3000{path}"

        # Forward headers from Waitress → Next.js
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                if header_name.lower() not in HOP_BY_HOP:
                    headers[header_name] = value
        if environ.get("CONTENT_TYPE"):
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if environ.get("CONTENT_LENGTH"):
            headers["Content-Length"] = environ["CONTENT_LENGTH"]

        # Make request with streaming enabled
        try:
            resp = http.request(
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
        response_headers = [
            (k, v) for k, v in resp.headers.items()
            if k.lower() not in HOP_BY_HOP
        ]

        # Streaming body iterator
        def body_iter():
            for chunk in resp.stream(amt=None):
                if chunk:
                    yield chunk
            resp.release_conn()

        start_response(status_line, response_headers)
        return body_iter()
    
    def app(environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # if the request targets /find4u, give it to find4u
        if path.startswith('/find4u'):
            return find4u_wsgi(environ, start_response)
        
        # otherwise, fall back to Finder
        return finder_wsgi(environ, start_response)
    
    def close():
        find4u_popen.terminate()
    
    return (app, close)

def main():
    logging.getLogger('waitress').setLevel(logging.INFO)
    
    # create reverse proxy
    app, close = reverse_proxy()
    
    # start Waitress on port 80
    print("Listening on http://localhost, ^C to exit")
    try:
        serve(app, listen="*:80")
    except:
        close()

if __name__ == "__main__":
    main()