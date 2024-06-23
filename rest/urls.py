from django.conf.urls import include
from django.contrib import admin
from django.urls import path
from rest_framework.routers import DefaultRouter
from api import views
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'user', views.UserViewSet)
router.register(r'blog', views.BlogViewSet)
router.register(r'category', views.CategoryViewSet)
router.register(r'tag', views.TagViewSet)
router.register(r'contact', views.ContactCreateView)


urlpatterns = [
	path('ckeditor/', include('ckeditor_uploader.urls')),   
	path('admin/', admin.site.urls),
	path('api/', include(router.urls)),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
