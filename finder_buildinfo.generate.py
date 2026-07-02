import shutil
import subprocess
from datetime import date

try:
    import finder_buildinfo
except:
    finder_buildinfo = None

with open("finder_buildinfo.py", "w") as f:
    print(f"BUILDDATE = {date.today().isoformat()!r}", file=f)
    if git := shutil.which("git"):
        print(f"BUILDCOMMIT = {subprocess.run(
            [git, "rev-parse", "--short", "HEAD"], capture_output=True,
            text=True
        ).stdout.strip()!r}", file=f)
        print(f"BUILDBRANCH = {subprocess.run(
            [git, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
            text=True
        ).stdout.strip()!r}", file=f)
    elif finder_buildinfo:
        print("git was not found, reusing previous BUILDCOMMIT and "
              "BUILDBRANCH")
        print(f"BUILDCOMMIT = {finder_buildinfo.BUILDCOMMIT!r}", file=f)
        print(f"BUILDBRANCH = {finder_buildinfo.BUILDBRANCH!r}", file=f)
    else:
        print("git was not found, a previous finder_buildinfo.py was not"
              "either, setting BUILDCOMMIT and BUILDBRANCH to 'unknown'")
        print("BUILDCOMMIT = 'unknown'", file=f)
        print("BUILDBRANCH = 'unknown'", file=f)