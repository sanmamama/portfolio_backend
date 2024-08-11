from django.conf.urls import include
from django.contrib import admin
from django.urls import path,re_path
from rest_framework.routers import DefaultRouter
from api import views
from django.conf import settings
from django.conf.urls.static import static
from api.views import LikeBlogView



router = DefaultRouter()
router.register(r'blog', views.BlogFilterViewSet)
router.register(r'category', views.CategoryViewSet)
router.register(r'tag', views.TagViewSet)
router.register(r'contact', views.ContactCreateView)

postterRouter = DefaultRouter()
postterRouter.register(r'user', views.UserViewSet, basename='user')
postterRouter.register(r'post', views.PostViewSet, basename='post')
postterRouter.register(r'follow', views.FollowViewSet, basename='follow')
postterRouter.register(r'like', views.LikeViewSet, basename='like')
postterRouter.register(r'message', views.MessageUserListViewSet, basename='message')
postterRouter.register(r'memberlist', views.MemberListViewSet, basename='memberlist')
postterRouter.register(r'listdetail', views.MemberListDetailViewSet, basename='listdetail')
postterRouter.register(r'addmember', views.AddMemberViewSet, basename='addmember')
postterRouter.register(r'repost', views.RepostViewSet, basename='repost')
postterRouter.register(r'notification', views.NotificationViewSet,basename='notification')




urlpatterns = [ 
	path('markdownx/', include('markdownx.urls')),
	path('admin/', admin.site.urls),

	path('api/', include(router.urls)),

	path('api/blog/<int:pk>/like/', LikeBlogView.as_view(), name='like'),

	path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
	path('api/auth/guest-login/', views.GuestLoginView.as_view(), name='guest-login'),

	path('api/postter/', include(postterRouter.urls)),
	

	
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
