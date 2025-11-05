# cusc_edx_api/urls.py
from django.urls import path

from . import views

app_name = "cusc_edx_api"

urlpatterns = [
    path("ping/", views.ping, name="ping"),

    # ecommerce
    path("orders/", views.order_list, name="order-list"),                # GET
    path("orders/create/", views.create_order, name="order-create"),     # POST
    path("orders/<int:order_id>/", views.order_detail, name="order-detail"),  # GET
    path("orders/<int:order_id>/status/", views.update_order_status, name="order-status"),  # POST
    
    # lookup user
    path("users/lookup/", views.user_lookup, name="user-lookup"),
]
