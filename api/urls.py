from django.urls import path
from .views import LikeBlogView

urlpatterns = [
	path('like/', LikeBlogView.as_view(), name='like'),
]
