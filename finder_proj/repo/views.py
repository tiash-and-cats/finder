from django.http import HttpResponse
from django.shortcuts import render
from git import Repo, NULL_TREE
from git.exc import GitCommandError
from django.utils.safestring import mark_safe
from .git_view import git_http_view
from django.http import Http404
from django.conf import settings
import html
import markdown

REPO_PATH = str(settings.BASE_DIR.parent)

def render_diff_text(diff_text):
    """Convert raw Git diff text into stylized HTML with <ins>/<del>."""
    lines = diff_text.splitlines()
    rendered = []
    for line in lines:
        escaped = html.escape(line)
        if line.startswith('+') and not line.startswith('+++'):
            rendered.append(f"<ins>{escaped}</ins>")
        elif line.startswith('-') and not line.startswith('---'):
            rendered.append(f"<del>{escaped}</del>")
        else:
            rendered.append(escaped)
    return '\n'.join(rendered)

def commit_view(request, commit_hash):
    repo = Repo(REPO_PATH)
    commit = repo.commit(commit_hash)

    try:
        if commit.parents:
            diffs = []
            for parent in commit.parents:
                diffs.extend(parent.diff(commit, create_patch=True))
        else:
            diffs = commit.diff(NULL_TREE, create_patch=True)
    except Exception as e:
        diffs = []
        # log error if needed

    file_changes = []
    for diff in diffs:
        change_type = (
            "added" if diff.new_file else
            "deleted" if diff.deleted_file else
            "renamed" if diff.renamed else
            "modified"
        )
        file_changes.append({
            "path": diff.b_path or diff.a_path,
            "change_type": change_type,
            "diff_html": render_diff_text(diff.diff.decode("utf-8", errors="replace"))
        })
    
    full_msg = commit.message or ""
    summary = commit.summary or ""
    
    desc_raw = full_msg[len(summary):].lstrip("\n")
    desc_html = mark_safe(markdown.markdown(desc_raw, extensions=["fenced_code", "tables"]))
    

    # Find all branches that contain this commit
    branches = [
        head.name for head in repo.heads
        if commit in repo.iter_commits(head.name)
    ]

    return render(request, "commit.html", {
        "commit": commit,
        "file_changes": file_changes,
        "desc_html": desc_html,
        "branches": branches,
    })

def repo_index(request):
    repo = Repo(REPO_PATH)
    commits = list(repo.iter_commits("master", max_count=5))
    branches = [head.name for head in repo.heads]

    return render(request, "index.html", {
        "commits": commits,
        "branches": branches,
    })

def commit_list(request):
    repo = Repo(REPO_PATH)
    commits = list(repo.iter_commits('--all'))
    return render(request, "commit_list.html", {
        "commits": commits
    })

def branch_view(request, branch_name):
    try:
        repo = Repo(REPO_PATH)
        branch_ref = repo.heads[branch_name]
        commits = list(repo.iter_commits(branch_ref, max_count=20))
    except (IndexError, ValueError, AttributeError):
        raise Http404("Branch not found.")

    commit_data = [
        {
            "hash": c.hexsha,
            "message": c.summary,
            "author": c.author.name,
            "date": c.committed_datetime.strftime("%Y-%m-%d")
        }
        for c in commits
    ]

    return render(request, "branch_view.html", {
        "branch_name": branch_name,
        "commits": commit_data
    })