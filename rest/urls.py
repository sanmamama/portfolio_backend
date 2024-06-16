from django.conf.urls import include
from django.contrib import admin
from django.urls import path
from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter()
router.register(r'user', views.UserViewSet)

urlpatterns = [
    path('api/', include(router.urls)),  
]
