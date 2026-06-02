# Security!

How fun and definitely not boring it is! But let's be serious. You might know that you can clone Finder by doing the following:
``` bash
git clone http://<finder-url>/repo/repo.git
```
But if we allowed pushes from those clones, then anybody could put their code on Finder. Anybody. Which includes bad people that go hack hack hack. Commit `de0f88f` goes into detail about this.

```
commit de0f88fae3faa8b428478753ffdc8604d7c1b2c9
Author: tiashDev <rbmtiash@gmail.com>
Date:   Tue Jun 24 23:47:30 2025 +0600

    feat(repo): block pushes from public clones

    Disable receive-pack to prevent direct pushes from repo clones

    This patch rejects all `git push` attempts to the `git-receive-pack` endpoint—
    specifically those coming from clones like:

        git clone http://<finder-url>/repo/repo.git

    Until Finder implements a proper push proposal system, we are disallowing
    direct pushes to prevent arbitrary code injection. This protects against
    scenarios where malicious or unreviewed changes are introduced to the server's
    repository, which could otherwise lead to security issues during deployment.

    The rejection is graceful and Git-compatible: we return sideband-encoded
    progress and error messages over a valid pkt-line stream, with a clean
    protocol flush (`0000`). Users are shown a clear explanation and directed to
    this commit for context.

    This guardrail can be lifted once push proposals are implemented with sandboxing
    and review guarantees.

    Example error message:

        remote: ----------- Finder -----------
        remote: For security reasons, until
        remote: we add push proposals, Finder
        remote: will not accept `git push`.
        remote: Please read commit xxxxxxx
        remote: for details.
        remote: ------------------------------
        remote: Push rejected by Finder.

        fatal: the remote end hung up unexpectedly
        error: failed to push some refs to 'http://<finder-url>/repo/repo.git'

    where `xxxxxxx` is whatever commit hash this commit ends up with.
```