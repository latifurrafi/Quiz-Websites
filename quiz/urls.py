from django.urls import path

from . import views

app_name = "quiz"

urlpatterns = [
    path("", views.home, name="home"),
    path("start/", views.start, name="start"),
    path("next/", views.reset, name="reset"),
    path("q/<uuid:token>/", views.play, name="play"),
    path("q/<uuid:token>/submit/", views.submit, name="submit"),
    path("q/<uuid:token>/result/", views.result, name="result"),
]
