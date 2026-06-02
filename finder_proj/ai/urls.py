from django.urls import path
from . import views

app_name = "ai"  # THIS is what registers the 'ai' namespace

urlpatterns = [
    path("chat/", views.chat, name="chat"),
]