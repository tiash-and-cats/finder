You may notice that the initial commit for this repo is not "Initial commit" or "Initial import from somewhere" or "A fresh start" or anything like that. It's "Migrated to new laptop". Why? This repo used to be closed source on OneDrive that was only accessible to me. When copying it over to my new laptop, I didn't copy the `.git` folder as it was taking too long. So here is the `git log` of that old Git repo. Note that this is before this repo's initial commit; no actual Find4U or Find4U CLI at this time, just Finder and router.py (which was later scrapped 2536fff) and dreams of Find4U.

`````
commit f57f621d96c0e278a6973a094fffdc9c9c420d0d (HEAD -> master)
Author: tiashDev <rbmtiash@gmail.com>
Date:   Thu Jan 8 22:51:41 2026 +0600

    Fixed (and improved) repo cloning

    Now the bare repo path is derived from settings.BASE_DIR. Here's the new
    tutorial on how to clone Finder. This was tested on Windows only; sorry
    Linux fans...

    Prerequisites:

    - Git and Python
    - A basic understanding of both
    - A basic understanding of Django

    **Step 1:** Clone the repo

    ``` batch
    git clone http://<finder-url>/repo/repo.git
    ```

    **Step 2:** Create bare repo

    ``` batch
    cd repo
    mkdir bare
    git clone --bare . bare/repo.git
    ```

    Verify:
    ``` batch
    cd bare/repo.git
    git log
    ```

    **Step 3:** Create venv:

    ``` batch
    python -m venv env
    pip install -r requirements.txt
    ```

    **Step 4:** Database magic:

    ``` batch
    cd finder_proj
    python manage.py migrate
    ```

    **Step 5:** Indexing

    ```
    (env) C:\Users\Dell\finder-clone\repo\finder_proj>python manage.py shell
    8 objects imported automatically (use -v 2 for details).

    Python 3.13.9 (tags/v3.13.9:8183fa5, Oct 14 2025, 14:09:13) [MSC v.1944 64 bit (AMD64)] on win32
    Type "help", "copyright", "credits" or "license" for more information.
    (InteractiveConsole)
    >>> import crawl
    >>> crawl.start_crawl("seed")
    crawling site https://www.w3schools.com/django
        new site https://www.w3schools.com/django added
        crawling site https://www.w3schools.com
            new site https://www.w3schools.com added
            crawling site https://www.w3schools.com/videos
                new site https://www.w3schools.com/videos added
            crawling site https://www.w3schools.com/html
                new site https://www.w3schools.com/html added
                crawling site https://www.w3schools.com/tags
                    new site https://www.w3schools.com/tags added
                ...
    ```
    Let this run for a few minutes to index a good number of pages.

    **Step 6:** Enjoy!

    ```
    python manage.py runserver
    ```

commit 666e8a2b2842d3609d51b117d0757d0deebc6bcc (origin/master)
Author: tiashDev <rbmtiash@gmail.com>
Date:   Thu Jan 8 22:14:59 2026 +0600

    Add SECURITY.md

    Nothing much to say. SECURITY.md has security info.

commit bc4a384ea108f23d128ef30de0c64f710da15c82
Author: tiashDev <rbmtiash@gmail.com>
Date:   Thu Jan 8 21:43:49 2026 +0600

    YIKES! Entire repo history got corrupted - starting again

    I wish I was joking. So after moving to a fresh install of Windows, I
    tried to use Finder. It worked. Then I tried to navigate to the repo
    dashboard. Flawless. But then I tried to look at a commit. Disaster!

    ```
    git.exc.GitCommandError: Cmd('git') failed due to: exit code(128)
      cmdline: git diff-tree ea1f3732b1095a3733c882776815e2e76c2ba2b3 03fd1f80a0f749f9d36a883ea5d141918b8a8c23 -r --abbrev=40 --full-index -M -p --no-ext-diff --no-color
    ```

    I checked integrity using `git fsck --full`. It was bad. To say that was
    an understatement would in itself be the understatement of the century.
    So I had to start again. This was the old history upto the furthest I
    could go back in time.

    ````
    commit 03fd1f80a0f749f9d36a883ea5d141918b8a8c23 (HEAD -> master)
    Author: tiashDev <rbmtiash@gmail.com>
    Date:   Thu Jun 26 00:57:31 2025 +0600

        GIT_PUSH_ENABLED option added in settings.py; Finder licensed under GNU GPLv3

        The new `GIT_PUSH_ENABLED` option in `settings.py` looks like the following:

        ``` python
        GIT_PUSH_ENABLED = False # Specifies if `git push` requests to `/repo/repo.git` should be allowed
                                 # Obviously False here, for security reasons, but you can change this to True if you so wish!
                                 # Read commit de0f88f for more info about the security implications of setting this to True.
        ```

        And the new license:

        ```
        Finder - Copyright (C) 2025 Ridwan

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program. If not, see <https://www.gnu.org/licenses/>.
        ```

    commit ea1f3732b1095a3733c882776815e2e76c2ba2b3
    Author: tiashDev <rbmtiash@gmail.com>
    Date:   Tue Jun 24 23:53:27 2025 +0600

        modify git_view.py to reflect actual commit hash

        This patch changes the placeholder `xxxxxxx` hash with the actual, real hash for the commit: `de0f88f`

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

    commit 6740a24fda57da94969dc990dfaae2dbc84b42ea (origin/master)
    Author: tiashDev <rbmtiash@gmail.com>
    Date:   Tue Jun 24 18:32:44 2025 +0600

        Added test to make sure people can commit their clones

    commit ad71c1c06dbecd398724bfcdad0dc9f301ff678a
    Author: tiashDev <rbmtiash@gmail.com>
    Date:   Tue Jun 24 17:48:37 2025 +0600

        Added requirements.txt + added "bare" to .gitignore

        As bare is added to .gitignore now, it won't be tracked anymore - great!

        Also I added a branch view that you can find at `/repo/branch/<branch-name>/`, which shows the last 20 commits on the branch with the name `<branch-name>`. I also added a **Branches** section to `/repo/` that lists all the branches with links.

        Now, here is the new cloning process for Finder with the new requirements.txt:

        Prerequisites:

        - A virtual environment: You can create one by running `python -m venv env`, which will create a new virtual environment called `env`.
        - An installation of Git
        - An installation of Python
        - A basic understanding of both

        Then,

        1. Clone the repo:
        ``` bash
        git clone http://<finder-url>/repo/repo.git
        ```
        2. Install the dependencies:
        ``` bash
        pip install -r requirements.txt
        ```

        And now you have a nice install of Finder! Before you can use it, you have to run:
        ``` bash
        cd finder_proj
        python manage.py migrate
        ```
        to make the database and the tables in the database. To run the server, run:
        ``` bash
        python manage.py runserver
        ```
        But to index things, there is a script called `crawl.py`. Given are some seed files. To run it:
        ```
        (env) $ python manage.py shell
        8 objects imported automatically (...)

        Python 3.*.* (...; ...)
        (InteractiveConsole)
        >>> import crawl
        >>> crawl.start_crawl("seed") # Runs the crawler on the seed file "seed"
        crawling site https://www.w3schools.com/django/index.php
            ...
        ```
        And enjoy!

    commit 429ea34c4c28377f3765d6d0aef9868fe783a08a
    Author: tiashDev <rbmtiash@gmail.com>
    Date:   Tue Jun 24 16:32:14 2025 +0600

        Added `git clone` support

        Now, you can do:

        ``` bash

        git clone http://<finder-url>/repo/repo.git

        ```

        And the latest version of Finder will be cloned to your computer!

        `git push` support is underway, and so is a requirements.txt, but those will be coming soon!
    ````
`````