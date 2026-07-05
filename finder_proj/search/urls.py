from django.urls import path
from . import views

app_name = "search"

def trigger_error(request):
    raise Exception("Test 500 error")

urlpatterns = [
    path('', views.search, name='search'),
    path('search/', views.search_results, name='search_results'),
    path('indexed/', views.indexed, name='all_indexed'),
    path("500/", trigger_error, name="ops"),
]