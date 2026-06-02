# repo/urls.py
from django.urls import path
from . import views

app_name = "repo"

urlpatterns = [
    path("", views.repo_index, name="index"),  # Optional: landing page for /repo/
    path("commit/", views.commit_list, name="commit_list"),
    path("commit/<str:commit_hash>/", views.commit_view, name="commit"),
    path("branch/<str:branch_name>/", views.branch_view, name="branch"),  # Future use
    path("repo.git/<path:path>", views.git_http_view),
]