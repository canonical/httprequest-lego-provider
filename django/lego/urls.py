"""Urls."""

from django.urls import path

from . import views

urlpatterns = [
    path("cleanup/", views.handle_cleanup, name="cleanup"),
    path("present/", views.handle_present, name="present"),
    
]