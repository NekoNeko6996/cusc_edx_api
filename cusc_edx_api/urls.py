# cusc_edx_api/urls.py
from django.urls import path
from . import views

app_name = "cusc_edx_api"

urlpatterns = [
    path("api/cusc-edx-api/ping/", views.ping, name="ping"),
    re_path(r"^api/cusc-edx-api/", include("cusc_edx_api.urls")),
]
