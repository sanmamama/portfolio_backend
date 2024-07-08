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
from .serializer import BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer,UserSerializer,PostSerializer,FollowSerializer,LikeSerializer,FollowUserDetailSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination

from django.db.models import Q


#イカ、ポスッター

        

class LikeViewSet(mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = self.request.user.id
        post_id = serializer.validated_data.get('post').id
        print(user_id,post_id)
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=self.request.user, post=post)
        if not created:
            like.delete()  # 既に「いいね」している場合は「いいね」を解除
            return Response({"message": "いいねを取り消しました"}, status=status.HTTP_200_OK)

        return Response({"message": "いいねしました"}, status=status.HTTP_200_OK)

class FollowViewSet(mixins.CreateModelMixin,viewsets.GenericViewSet): #viewsets.GenericViewSetはlist無効（/へのGETメソッド無効）
    permission_classes = [IsAuthenticated]
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

    @action(detail=False, methods=['get'], url_path='me')
    def me_following(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(follower=user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='(?P<uid>[^/.]+)/following')
    def following(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            queryset = self.get_queryset().filter(follower=user)
            paginator = PageNumberPagination()
            #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
            result_page = paginator.paginate_queryset(queryset, request)
            serializer = FollowUserDetailSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response({"detail": "ユーザーが見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='(?P<uid>[^/.]+)/follower')
    def follower(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            queryset = self.get_queryset().filter(following=user)
            paginator = PageNumberPagination()
            #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
            result_page = paginator.paginate_queryset(queryset, request)
            serializer = FollowUserDetailSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        return Response({"detail": "ユーザーが見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)

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
    class CustomPageNumberPagination(PageNumberPagination):
        page_size = 6  # ここでページサイズを指定します

    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer
    
    

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if instance.owner != request.user:
            raise PermissionDenied("自分の投稿以外は編集できません。")
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.owner != request.user:
            raise PermissionDenied("自分の投稿以外は削除できません。")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='user/(?P<uid>[^/.]+)')
    def posts_by_user(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            posts = Post.objects.filter(owner=user).order_by('created_at').reverse()
            paginator = PageNumberPagination()
            #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
            result_page = paginator.paginate_queryset(posts, request)
            serializer = PostSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response({"detail": "ユーザーが見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)
    
    def get_queryset(self):
        following_ids = Follow.objects.filter(follower_id=self.request.user.id).values('following_id')
        queryset = Post.objects.filter( Q(owner_id=self.request.user.id) | Q(owner_id__in=following_ids)).order_by('-created_at')
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=['get'], url_path='(?P<uid>[^/.]+)')
    def user_data(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            serializer = UserSerializer(user)
            return Response(serializer.data)
        return Response({"detail": "ユーザーが見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)
    
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
