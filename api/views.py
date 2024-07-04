from rest_framework.views import APIView
from dj_rest_auth.registration.views import RegisterView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins,viewsets
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from .filters import BlogFilter
from .models import *
from .serializer import BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer,UserSerializer,PostSerializer,FollowSerializer,LikeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404


#イカ、ポスッター

class LikeViewSet(viewsets.ReadOnlyModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

class FollowViewSet(viewsets.ReadOnlyModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Post.objects.all().order_by('created_at').reverse()
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return User.objects.filter(email=self.request.user.email)
    
    def patch(self, request, *args, **kwargs):
        # instanceの取得
        instance = get_object_or_404(User, pk=self.request.user.id)

        # シリアライザの作成
        print(request.data)
        serializer = UserSerializer(instance=instance, data=request.data, partial=True)

        # バリデーション
        serializer.is_valid(raise_exception=True)

        # DB更新
        serializer.save()

        return Response({'result':True})

#イカ、ブログ#

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
