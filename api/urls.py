from django.urls import path
from .views import UserViewSet,IndexView

urlpatterns = [
	path('', IndexView.as_view(), name='index'),
    path('api/', UserViewSet.as_view(), name='api'),
]