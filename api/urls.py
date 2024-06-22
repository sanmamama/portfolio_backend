from django.urls import path
from .views import UserViewSet

urlpatterns = [
	
]

from django.urls import path
from .views import BlogList, BlogDetail

urlpatterns = [
    #path('blogs/', BlogList.as_view(), name='blog-list'),
    #path('blogs/<int:pk>/', BlogDetail.as_view(), name='blog-detail'),
]