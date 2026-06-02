"""
This file is explained in this diagram:

                                         request
                                            |
                                            v
                                -------------------------
                                | router.py (this file) |
                                -------------------------
									        |
                                            v
								      -------------
									  | check url |
									  -------------
                  (Medio) medio.localhost   |   localhost (Finder)
              |---------------------------------------------------------|
              v                                                         v
    -----------------------                             -----------------------------
    | display placeholder |                             | return result of request  |
    -----------------------                             | to localhost:8000 (Django |
                                                        | is serving there)         |
                                                        -----------------------------

"""

from wsgiref.simple_server import make_server
from wsgiref.util import request_uri, FileWrapper, is_hop_by_hop
from urllib import request, parse
from urllib.error import HTTPError
from re import compile as regex

subdomainre = regex(r"^(?P<subdomain>[a-zA-Z0-9-]+)\..+$")

def format_header_name(header):
    words = header[5:].split('_')  # Remove 'HTTP_' and split by '_'
    return '-'.join(word.capitalize() for word in words)  # Capitalize each segment

def handle_response(start_response, req):
    try:
        res = request.urlopen(req)
    except HTTPError as e:
        start_response(f"{e.code} {e.reason}", [(k, v) for k, v in e.headers.items() if not is_hop_by_hop(k)])
        return FileWrapper(e)
    start_response('200 OK', res.getheaders())
    return FileWrapper(res)

getparsedurl = lambda environ: parse.urlparse(request_uri(environ))

geturl = lambda environ: getparsedurl(environ)._replace(netloc="", scheme="").geturl()

def getsubdomain(environ): 
    match = subdomainre.match(getparsedurl(environ).netloc)
    if match is not None:
        return match["subdomain"]
    else:
        return ""

def app(environ, start_response):
    headers = {format_header_name(key): value for key, value in environ.items() if key.startswith('HTTP_')}
    request_type = environ['REQUEST_METHOD']
    
    if request_type == "GET":
        if getsubdomain(environ) == "medio":
            start_response("200 OK", [("Content-Type", "text/html")])
            return [b"""\
<!DOCTYPE html>
<html>
<body>

<h1>Medio coming soon!</h1>
<p>Medio is a video streaming service like YouTube (imaginary for now).</p>
<p><a href="//localhost/">Back to Finder</a></p>

</body>
</html>\
"""]
        reqpath = geturl(environ)
        req = request.Request(f"http://localhost:8000{reqpath}", headers=headers)
        return handle_response(start_response, req)
    elif request_type == "POST":
        if getsubdomain(environ) == "medio":
            start_response("200 OK", [("Content-Type", "text/html")])
            return [b"""\
<!DOCTYPE html>
<html>
<body>

<h1>Medio coming soon!</h1>
<p>Medio is a video streaming service like YouTube (imaginary for now).</p>
<p><a href="//localhost/">Back to Finder</a></p>

</body>
</html>\
"""]
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            content_length = 0
        
        post_data = environ['wsgi.input'].read(content_length)  # Read the POST body
        req = request.Request(f"http://localhost:8000{geturl(environ)}", data=post_data, headers=headers)
        print(geturl(environ))
        return handle_response(start_response, req)
        

with make_server('', 80, app) as server:
    print("Serving at http://localhost/...")
    server.serve_forever()