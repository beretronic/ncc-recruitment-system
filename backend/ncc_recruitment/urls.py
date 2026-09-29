from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("recruitment.urls")),
]

if settings.DEBUG:
    # Media files (CVs) are exempted from X-Frame-Options so they can be
    # previewed inline in the HR review modal's <iframe> - the frontend
    # (localhost:5173) and backend (127.0.0.1:8000) are different origins,
    # so without this exemption the browser blocks the CV from displaying
    # in the frame, even locally. The rest of the site (API, admin) keeps
    # the default X-Frame-Options protection.
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            xframe_options_exempt(serve),
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
