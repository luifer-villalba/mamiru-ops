from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic import RedirectView
from django.views.static import serve


def healthz(_request):
    return JsonResponse({"status": "ok"})


media_url_path = settings.MEDIA_URL.strip("/")
media_urlpatterns = []

if settings.DEBUG:
    media_urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA_FILES and media_url_path:
    media_urlpatterns = [
        re_path(
            rf"^{media_url_path}/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]

urlpatterns = [
    path("healthz/", healthz),
    path("admin/", RedirectView.as_view(url=reverse_lazy("admin:index"), permanent=True)),
    path("api/", include("catalog.urls")),
    *media_urlpatterns,
    path("", RedirectView.as_view(url=reverse_lazy("admin:catalog_product_changelist"), permanent=False)),
    path("", admin.site.urls),
]
