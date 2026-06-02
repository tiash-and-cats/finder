import subprocess
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os

GIT_PROJECT_ROOT = str(settings.BASE_DIR.parent / "bare")

if os.name == "nt":
    GIT_HTTP_BACKEND = "C:/Program Files/Git/mingw64/libexec/git-core/git-http-backend.exe"
else:
    GIT_HTTP_BACKEND = "git-http-backend"

@csrf_exempt
def git_http_view(request, path):
    env = os.environ.copy()
    
    if path.endswith("git-receive-pack") and request.method == "POST" and not settings.GIT_PUSH_ENABLED:
        def pkt_line(data: bytes) -> bytes:
            return f"{len(data) + 4:04x}".encode() + data
        
        response = (
            pkt_line(f"\x02{' Finder '.center(30, '-')}\n".encode()) +
            pkt_line(b"\x02For security reasons, until \n") +
            pkt_line(b"\x02we add push proposals, Finder \n") +
            pkt_line(b"\x02will not accept `git push`. \n") +
            pkt_line(b"\x02Please read commit de0f88f \n") +
            pkt_line(b"\x02for details.\n") +
            pkt_line(f"\x02{'-'*30}\n".encode()) +
            pkt_line(b"\x03Push rejected by Finder.\n") +
            b"0000"
        )
        
        return HttpResponse(
            response,
            status=200,
            content_type="application/x-git-receive-pack-result"
        )
    
    env["GIT_PROJECT_ROOT"] = GIT_PROJECT_ROOT
    env["GIT_HTTP_EXPORT_ALL"] = ""
    env["REMOTE_USER"] = request.user.username if request.user.is_authenticated else "anonymous"
    env["PATH_INFO"] = "/repo.git/" + path
    env["REQUEST_METHOD"] = request.method
    env["QUERY_STRING"] = request.META.get("QUERY_STRING", "")
    env["CONTENT_TYPE"] = request.META.get("CONTENT_TYPE", "")
    env["GATEWAY_INTERFACE"] = "CGI/1.1"
    env["SCRIPT_NAME"] = ""
    env["REMOTE_ADDR"] = request.META.get("REMOTE_ADDR", "")
    env["AUTH_TYPE"] = ""
    env["HTTP_USER_AGENT"] = request.META.get("HTTP_USER_AGENT", "")
    
    print("PATH_INFO:", env["PATH_INFO"])
    print("QUERY_STRING:", env["QUERY_STRING"])

    input_data = request.body if request.method == "POST" else None

    p = subprocess.Popen(
        [GIT_HTTP_BACKEND],
        stdin=subprocess.PIPE if input_data else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    stdout, stderr = p.communicate(input=input_data)

    if p.returncode != 0:
        return HttpResponse(
            f"Git backend error:\n{stderr.decode(errors='replace')}",
            status=500,
            content_type="text/plain"
        )

    header_blob, _, body = stdout.partition(b"\r\n\r\n")
    headers = header_blob.decode(errors="replace").split("\r\n")

    response = HttpResponse(body)

    for header_line in headers:
        if header_line:
            key, _, value = header_line.partition(": ")
            response[key] = value

    return response