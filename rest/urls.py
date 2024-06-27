from django.conf.urls import include
from django.contrib import admin
from django.urls import path,re_path
from rest_framework.routers import DefaultRouter
from api import views
from django.conf import settings
from django.conf.urls.static import static
from api.views import LikeBlogView,CustomConfirmEmailView



router = DefaultRouter()
#router.register(r'user', views.UserViewSet)
router.register(r'blog', views.BlogFilterViewSet)
router.register(r'category', views.CategoryViewSet)
router.register(r'tag', views.TagViewSet)
router.register(r'contact', views.ContactCreateView)


urlpatterns = [
	path('ckeditor/', include('ckeditor_uploader.urls')),   
	path('admin/', admin.site.urls),
	path('api/', include(router.urls)),
	path('api/blog/<int:pk>/like/', LikeBlogView.as_view(), name='like'),

	#path('accounts/', include('allauth.urls')),
	#re_path('api/auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$', CustomConfirmEmailView.as_view(),name='account_confirm_email',),
	path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
	
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
