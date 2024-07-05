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
from rest_framework.exceptions import ValidationError


#イカ、ポスッター

class LikeViewSet(viewsets.ReadOnlyModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

class FollowViewSet(mixins.CreateModelMixin,viewsets.GenericViewSet): #viewsets.GenericViewSetはlist無効（/へのGETメソッド無効）
    permission_classes = [IsAuthenticated]
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

    @action(detail=False, methods=['get'], url_path='following')
    def following(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(follower=user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='follower')
    def follower(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(following=user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        following_id = serializer.validated_data.get('following').id
        follower_id = self.request.user.id

        if following_id == follower_id:
            raise ValidationError("自分自身をフォローすることはできません。")

        existing_follow = Follow.objects.filter(follower_id=follower_id, following_id=following_id).first()
        if existing_follow:
            existing_follow.delete()
            return Response({"message": "フォローを解除しました。"}, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"message": "フォローしました。"}, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

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
        instance = get_object_or_404(User, pk=self.request.user.id)
        serializer = UserSerializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
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
