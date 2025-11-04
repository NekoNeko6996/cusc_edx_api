# cusc_edx_api/apps.py
from django.apps import AppConfig

class CuscEdxApiConfig(AppConfig):
    name = "cusc_edx_api"
    label = "cusc_edx_api"
    verbose_name = "CUSC Edx API"

    plugin_app = {
        "url_config": {
            "lms.djangoapp": {
                "namespace": "cusc_edx_api",
                # prefix chung cho các URL của app này
                "regex": r"^api/cusc-edx-api/",
                # -> sẽ include cusc_edx_api/urls.py
                "relative_path": "urls",
            },
        },
    }   
