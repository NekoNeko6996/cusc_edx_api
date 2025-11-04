from django.urls import include, path
from lms import urls as lms_urls  # import URL gốc của LMS


# Bắt đầu từ toàn bộ urlpatterns gốc của LMS
urlpatterns = list(getattr(lms_urls, "urlpatterns", []))

# Thêm URL của plugin dưới prefix /api/cusc-edx-api/
urlpatterns += [
    path(
        "api/cusc-edx-api/",
        include(("cusc_edx_api.urls", "cusc_edx_api"), namespace="cusc_edx_api"),
    ),
]
