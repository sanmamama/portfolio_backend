from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from .filters import BlogFilter
from rest_framework.decorators import action
from .models import *
from .serializer import UserSerializer,BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer




class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class BlogFilterViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by('created_at').reverse()
    serializer_class = BlogSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BlogFilter

    @action(detail=False, methods=['get'])
    def all(self, request):
        posts = Blog.objects.all()
        serializer = BlogSerializer(posts, many=True)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class ContactCreateView(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


