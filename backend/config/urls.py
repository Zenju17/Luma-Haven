from django.urls import path, include
from django.views.generic import RedirectView
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
