"""
cusc_edx_api Django application initialization.
"""

# cusc_edx_api/apps.py
from django.apps import AppConfig

class CuscEdxApiConfig(AppConfig):
    """
    Cấu hình Django app cho cusc_edx_api.
    """
    name = "cusc_edx_api"
    label = "cusc_edx_api"
    verbose_name = "CUSC Edx API"

    # Cấu hình plugin tối thiểu: chỉ đăng ký urls cho LMS.
    plugin_app = {
        "url_config": {
            "lms.djangoapp": {
                "namespace": "cusc_edx_api",
                "relative_path": "urls",  # -> cusc_edx_api/urls.py
            },
        },
    }
