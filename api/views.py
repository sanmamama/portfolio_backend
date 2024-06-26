from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins,viewsets
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from .filters import BlogFilter
from rest_framework.decorators import action
from .models import *
from .serializer import UserSerializer,BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer




class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class BlogFilterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Blog.objects.all().order_by('created_at').reverse()
    serializer_class = BlogSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BlogFilter

    @action(detail=False, methods=['get'])
    def all(self, request):
        posts = Blog.objects.all()
        serializer = BlogSerializer(posts, many=True)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class ContactCreateView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class LikeBlogView(APIView):
    def patch(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        blog.likes += 1
        blog.save()
        return Response({'likes': blog.likes}, status=status.HTTP_200_OK)
