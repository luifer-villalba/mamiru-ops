from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic import RedirectView
from django.views.static import serve


def healthz(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("healthz/", healthz),
    path("admin/", RedirectView.as_view(url=reverse_lazy("admin:index"), permanent=True)),
    path("api/", include("catalog.urls")),
    path("", RedirectView.as_view(url=reverse_lazy("admin:catalog_product_changelist"), permanent=False)),
    path("", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA_FILES:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
