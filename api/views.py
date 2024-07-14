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
from .serializer import BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer,UserSerializer,PostSerializer,FollowSerializer,LikeSerializer,FollowUserDetailSerializer,MessageUserListSerializer,MemberListSerializer,MessageSerializer,MemberListDetailSerializer,MemberListCreateSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from django.db.models import Max

from django.db.models import Q


#イカ、ポスッター



class MessageUserListViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageUserListSerializer

    def get_queryset(self):
        # 最新のメッセージを取得
        latest_messages = Message.objects.filter(Q(user_from_id=self.request.user.id)|Q(user_to_id=self.request.user.id)).order_by('created_at').reverse()
        
        unique_messages = []
        seen_pairs = set()

        for message in latest_messages:
            pair = tuple(sorted([message.user_from.id, message.user_to.id]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_messages.append(message)
        
        return unique_messages
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='(?P<id>\d+)')
    def message_by_user(self, request, id=None):
        queryset = Message.objects.filter(Q(user_from_id=id,user_to_id=self.request.user.id)|Q(user_to_id=id,user_from_id=self.request.user.id)).order_by('created_at').reverse()
        paginator = PageNumberPagination()
        #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return MessageUserListSerializer
        elif self.request.method == 'POST':
            return MessageSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(user_from=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class MemberListViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return MemberListSerializer
        elif self.request.method == 'POST':
            return MemberListCreateSerializer
        elif self.request.method == 'PATCH':
            return MemberListCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        list_id = self.request.query_params.get('id', None)
        
        if list_id:
            return List.objects.filter(id=list_id,owner_id=self.request.user.id)
        return List.objects.filter(owner_id=self.request.user.id)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    
    
class MemberListDetailViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MemberListDetailSerializer

    @action(detail=False, methods=['get'], url_path='(?P<id>\d+)')
    def message_by_user(self, request, id=None):
        queryset = ListMember.objects.filter(list_id=id,list_id__owner=self.request.user.id)
        paginator = PageNumberPagination()
        #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_queryset(self):
        queryset = ListMember.objects.filter(list_id__owner=self.request.user.id)
        return queryset
    
    

class LikeViewSet(mixins.CreateModelMixin,viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated]
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = self.request.user.id
        post_id = serializer.validated_data.get('post').id

        if user_id == Post.objects.filter(id=post_id).first().owner_id:
            raise ValidationError("自分のポストをいいねすることはできません。")

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
        reply_ids = list(Reply.objects.filter(reply_to_id = self.request.user.id).values_list('post_id',flat=True))
        following_ids = list(Follow.objects.filter(follower_id=self.request.user.id).values_list('following_id',flat=True))
        queryset = Post.objects.filter( Q(owner_id=self.request.user.id) | Q(owner_id__in=following_ids) | Q(id__in=reply_ids)).order_by('-created_at')

        query = self.request.query_params.get('q', None)
        if query:
            return Post.objects.filter(Q(content__icontains=query)|Q(owner__username__icontains=query)|Q(owner__uid__icontains=query)).order_by('-created_at')
        

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
        user_id = self.request.query_params.get('id', None)
        if user_id:
            return User.objects.filter(id=user_id)
        q = self.request.query_params.get('q', None)
        if q:
            return User.objects.filter(Q(uid__icontains=q)|Q(username__icontains=q))
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
