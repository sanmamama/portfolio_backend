from rest_framework.views import APIView
from dj_rest_auth.registration.views import RegisterView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins,viewsets,permissions
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from .filters import BlogFilter
from .models import *
from .serializer import BlogSerializer,CategorySerializer,TagSerializer,ContactSerializer,UserSerializer,PostSerializer,FollowSerializer,LikeSerializer,FollowUserDetailSerializer,MessageUserListSerializer,MemberListSerializer,MessageSerializer,MemberListDetailSerializer,MemberListCreateSerializer,RepostSerializer,AddMemberSerializer,NotificationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from django.db.models import Max
from django.db.models import F
from django.db.models import Q
from .secrets import DEEPL_API_KEY
import requests
from rest_framework.authtoken.models import Token


#イカ、ポスッター

class GuestLoginView(APIView):
    def post(self, request):
        # 一意なゲストユーザー名を生成
        guest_username = f"guest_{uuid.uuid4().hex[:10]}"
        # パスワードなしでユーザーを作成
        guest_user = User.objects.create_user(username=guest_username,email=guest_username, password=None ,uid=guest_username ,avatar_imgurl="guest.png")
        # 必要ならば、その他のユーザー情報も設定
        guest_user.save()

        # ログイン用のトークンを生成（JWTやDRFトークンを使用している場合）
        # トークン生成処理を書く
        token, created = Token.objects.get_or_create(user=guest_user)

        return Response({
            'key': token.key,
        }, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ログインユーザーに関連する通知のみを返す
        return Notification.objects.filter(receiver=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        # 通知を既読にする
        ids = request.data.get('ids', [])
        Notification.objects.filter(id__in=ids, receiver=request.user).update(is_read=True)
        return Response({"status": "notifications marked as read"})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        unread_count = Notification.objects.filter(receiver=request.user, is_read=False).count()
        return Response(unread_count)

    def perform_create(self, serializer):
        # 通知を作成するとき、送信者と受信者を設定する
        serializer.save(sender=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        # 未読通知の数をカウント
        unread_count = Notification.objects.filter(receiver=request.user, is_read=False).count()
        
        if page is not None:
            Notification.objects.filter(pk__in=[notification.id for notification in page]).update(is_read=True)
            serializer = self.get_serializer(page, many=True)
            paginated_response = paginator.get_paginated_response(serializer.data)
            paginated_response.data['unread_count'] = unread_count  # 未読通知の数をレスポンスに追加
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'results': serializer.data,
            'unread_count': unread_count  # 未読通知の数をレスポンスに追加
        }
        return Response(response_data)

class AddMemberViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AddMemberSerializer

    def create(self, request, *args, **kwargs):
        list_id = request.data.get('list')
        user_id = request.data.get('user')
        
        try:
            # リストの所有者を確認
            list_instance = List.objects.get(id=list_id)
            if list_instance.owner.id != self.request.user.id:
                return Response({'error': 'You do not have permission to modify this list.'}, status=status.HTTP_403_FORBIDDEN)
        except List.DoesNotExist:
            return Response({'error': 'List not found.'}, status=status.HTTP_404_NOT_FOUND)


        try:
            member = ListMember.objects.get(list_id=list_id, user_id=user_id)
            member.delete()
            return Response({'message': 'Member removed successfully.'}, status=status.HTTP_200_OK)
        except ListMember.DoesNotExist:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    

class RepostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Repost.objects.all()
    serializer_class = RepostSerializer

    def create(self, request, *args, **kwargs):
        user = request.user
        post_id = request.data.get('post')
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        
        #通知
        if self.request.user != post.owner:
            notification, created = Notification.objects.get_or_create(sender=self.request.user,receiver=post.owner,notification_type="repost",content=post.content,post_id=post_id)

        if Repost.objects.filter(user=user, post=post).exists():
            Repost.objects.filter(user=user, post=post).delete()
            if self.request.user != post.owner:
                notification.delete()
            repost_count = Repost.objects.filter(post=post).count()
            return Response({"repost_count": repost_count}, status=status.HTTP_200_OK)

        repost = Repost(user=user, post=post)
        repost.save()
        repost_count = Repost.objects.filter(post=post).count()
        return Response({"repost_count": repost_count}, status=status.HTTP_201_CREATED)
    


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
    
    @action(detail=False, methods=['get'], url_path=r'(?P<id>\d+)')
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

        receiver_user = serializer.validated_data.get('user_to')
        message = serializer.validated_data.get('content')

        #通知
        if self.request.user != receiver_user:
            notification, created = Notification.objects.get_or_create(sender=self.request.user,receiver=receiver_user,notification_type="message",content=message)

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

    @action(detail=False, methods=['get'], url_path=r'(?P<id>\d+)')
    def message_by_user(self, request, id=None):
        queryset = ListMember.objects.filter(list_id=id,list_id__owner=self.request.user.id)
        paginator = PageNumberPagination()
        #paginator.page_size = 10  # 1ページあたりのアイテム数を設定    指定するなら
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete_by_ids(self, request):
        list_id = request.query_params.get('list_id')
        user_id = request.query_params.get('user_id')

        if not list_id or not user_id:
            return Response({'error': 'list_id and user_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = ListMember.objects.get(list_id=list_id, user_id=user_id)
            member.delete()
            return Response({'message': 'Member removed successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except ListMember.DoesNotExist:
            return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

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

        # if user_id == Post.objects.filter(id=post_id).first().owner_id:
        #     raise ValidationError("自分のポストをいいねすることはできません。")

        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=self.request.user, post=post)
        if self.request.user != post.owner:
            notification, _ = Notification.objects.get_or_create(sender=self.request.user,receiver=post.owner,notification_type="like",content=post.content,post_id=post_id)
        if not created:
            like.delete()  # 既に「いいね」している場合は「いいね」を解除
            if self.request.user != post.owner:
                notification.delete()
            like_count = Like.objects.filter(post=post).count()
            return Response({"like_count": like_count}, status=status.HTTP_200_OK)

        like_count = Like.objects.filter(post=post).count()
        return Response({"like_count": like_count}, status=status.HTTP_201_CREATED)

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
        
        notification, created = Notification.objects.get_or_create(sender=self.request.user,receiver=serializer.validated_data.get('following'),notification_type="follow",)

        existing_follow = Follow.objects.filter(follower_id=follower_id, following_id=following_id).first()
        if existing_follow:
            notification.delete()
            existing_follow.delete()
            return Response({"actionType": "unfollow","id": following_id}, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"actionType": "follow","id": following_id}, status=status.HTTP_201_CREATED, headers=headers)

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

    @action(detail=False, methods=['get'], url_path=r'reply/(?P<id>\d+)')
    def posts_by_reply(self, request, id=None):
        post = Post.objects.filter(parent=id).order_by('created_at').reverse()
        #print(post)

        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(post, request)
        
        if result_page is not None:
            Post.objects.filter(pk__in=[post.id for post in result_page]).update(view_count=F('view_count') + 1)
            serializer = self.get_serializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(post, many=True)
        return Response(serializer.data)

        # paginator = self.pagination_class()
        # result_page = paginator.paginate_queryset(post, request)
        # serializer = self.get_serializer(result_page, many=True)
        # return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], url_path='user/(?P<uid>[^/.]+)')
    def posts_by_user(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            posts = Post.objects.filter(owner=user)
            reposts = Repost.objects.filter(user_id=user).select_related('post')

            # 投稿とリツイートを統合
            timeline_posts = list(posts)
            timeline_reposts = [repost.post for repost in reposts]
            for repost in reposts:
                repost.post.repost = repost  # リポスト情報をポストに追加
                repost.post.sort = repost.created_at

            # postの方ソート用に
            for post in posts:
                post.sort = post.created_at
            
            timeline = timeline_posts + timeline_reposts
            timeline = sorted(timeline, key=lambda x: x.sort, reverse=True)

            # ソート用に使ったものを消します
            for post in timeline:
                if hasattr(post, 'sort'):
                    delattr(post, 'sort')

            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(timeline, request)
            
            if result_page is not None:
                Post.objects.filter(pk__in=[post.id for post in result_page]).update(view_count=F('view_count') + 1)
                serializer = self.get_serializer(result_page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(timeline, many=True)
            return Response(serializer.data)
        
        return Response({"detail": "ユーザーが見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)

    def get_queryset(self):
        return Post.objects.all()
    
    def filter_timeline(self, request):
        mention_ids = list(Mention.objects.filter(user_to_id=request.user.id).values_list('post_id', flat=True))
        following_ids = list(Follow.objects.filter(follower_id=request.user.id).values_list('following_id', flat=True))
        posts = Post.objects.filter(Q(owner_id=request.user.id) | Q(owner_id__in=following_ids) | Q(id__in=mention_ids))
        reposts = Repost.objects.filter(Q(user_id=request.user.id) | Q(user_id__in=following_ids)).select_related('post')
        
        timeline_posts = list(posts)
        timeline_reposts = [repost.post for repost in reposts]
        for repost in reposts:
            repost.post.repost = repost
            repost.post.sort = repost.created_at

        for post in posts:
            post.sort = post.created_at
        
        timeline = timeline_posts + timeline_reposts
        timeline = sorted(timeline, key=lambda x: x.sort, reverse=True)
        
        for post in timeline:
            if hasattr(post, 'sort'):
                delattr(post, 'sort')
        
        return timeline

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('q', None)
        if query:
            queryset = Post.objects.filter(Q(content__icontains=query) | Q(owner__username__icontains=query) | Q(owner__uid__icontains=query)).order_by('-created_at')
        else:
            queryset = self.filter_timeline(request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            Post.objects.filter(pk__in=[post.id for post in page]).update(view_count=F('view_count') + 1)
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Post.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        parent = serializer.validated_data.get('parent')
        message = serializer.validated_data.get('content')

        #翻訳
        def translate_text(text, target_lang):
            url = "https://api-free.deepl.com/v2/translate"
            data = {
                'auth_key': DEEPL_API_KEY,
                'text': text,
                'target_lang': target_lang,
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                # print(result) {'translations': [{'detected_source_language': 'EN', 'text': 'what are you doing now?'}]}
                return result['translations'][0]['detected_source_language'],result['translations'][0]['text']
            else:
                return None
            
        
            
        target_lang = "EN"
        detected_source_language,translated_text = translate_text(message, target_lang)
        serializer.save(content_EN=translated_text)

        if detected_source_language != "JA":
            target_lang = "JA"
            detected_source_language,translated_text = translate_text(message, target_lang)
            serializer.save(content_JA=translated_text)
        else:
            serializer.save(content_JA=message)


        if parent:
            post = Post.objects.filter(id=parent.id).first()
            #通知
            if self.request.user != post.owner:
                notification, created = Notification.objects.get_or_create(sender=self.request.user,receiver=post.owner,notification_type="reply",content=message,post_id=serializer.data['id'],parent=post)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['get'], url_path=r'(?P<uid>[^/.]+)')
    def user_data(self, request, uid=None):
        user = User.objects.filter(uid=uid).first()
        if user:
            serializer = UserSerializer(user, context={'request': request})
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
        serializer = UserSerializer(instance=instance, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

#イカ、ブログ#

class BlogFilterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Blog.objects.all().order_by('created_at').reverse()
    serializer_class = BlogSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BlogFilter

    @action(detail=False, methods=['get'])
    def all(self, request):
        posts = Blog.objects.all().order_by('created_at').reverse()
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
