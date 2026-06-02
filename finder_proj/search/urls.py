from django.urls import path
from . import views

app_name = "search"
urlpatterns = [
    path('', views.search, name='search'),
    path('search/', views.search_results, name='search_results'),
    path('indexed/', views.indexed, name='all_indexed'),
]