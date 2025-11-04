# cusc_edx_api/urls.py
from django.urls import path
from . import views

app_name = "cusc_edx_api"

urlpatterns = [
    # chỉ khai báo phần "đuôi" sau prefix
    path("ping/", views.ping, name="ping"),
]
