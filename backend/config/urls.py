from django.conf import settings
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core import views
from core.admin import luma_admin_site

urlpatterns = [
    path('', RedirectView.as_view(url='http://localhost:5173/staff', permanent=False)),
    path('admin/', luma_admin_site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/v1/', include(views.urlpatterns)),
]

if settings.DEBUG or settings.ENV == 'development':
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
