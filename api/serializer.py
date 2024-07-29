from rest_framework import serializers
from .models import *
from dj_rest_auth.registration.serializers import RegisterSerializer
from allauth.account.adapter import get_adapter
import re
#

from rest_framework import serializers
from django.conf import settings

class AbsoluteURLField(serializers.Field):
    def to_representation(self, value):
        request = self.context.get('request')
        if hasattr(value, 'url'):
            url = value.url
        else:
            url = value
        if request is not None and not url.startswith(('http://', 'https://')):
            ret = request.build_absolute_uri(url)
            return ret
        return url

#イカ、ポスッター

class AddMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListMember
        fields = '__all__'

class RepostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repost
        fields = ['id', 'user', 'post', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    user_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Message
        fields = ['id', 'user_to', 'content', 'created_at']
        read_only_fields = ['user_from', 'created_at']

    def create(self, validated_data):
        validated_data['user_from'] = self.context['request'].user
        return super().create(validated_data)



class UserSerializer(serializers.ModelSerializer):
    avatar_imgurl = AbsoluteURLField()
    post_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()
    follower = serializers.SerializerMethodField()
    like = serializers.SerializerMethodField()
    repost = serializers.SerializerMethodField()
    

    class Meta:
        model = User
        fields = ('id','uid','username','avatar_imgurl', 'profile_statement','post_count','following_count','follower_count','following','follower','like','repost') #,'email'

    def get_post_count(self, obj):#selfはシリアライザインスタンス自体を指しますが、objは現在シリアライザにバインドされているオブジェクト、すなわちシリアライザが処理しているモデルインスタンスを指します。
        return Post.objects.filter(owner=obj).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj).count()

    def get_follower_count(self, obj):
        return Follow.objects.filter(following=obj).count()
    
    def get_following(self, obj):
        fillowing_idx = list(Follow.objects.filter(follower=obj).values_list('following', flat=True))
        return fillowing_idx
    
    def get_follower(self, obj):
        fillower_idx = list(Follow.objects.filter(following=obj).values_list('follower', flat=True))
        return fillower_idx
    
    def get_like(self, obj):
        like_idx = list(Like.objects.filter(user=obj).values_list('post', flat=True))
        return like_idx
    
    def get_repost(self, obj):
        repost_idx = list(Repost.objects.filter(user=obj).values_list('post', flat=True))
        return repost_idx
    

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'sender', 'receiver', 'notification_type', 'content', 'is_read', 'created_at']
        read_only_fields = ['sender', 'receiver', 'created_at']



    
class MessageUserListSerializer(serializers.ModelSerializer):
    user_from = UserSerializer()
    user_to = UserSerializer()

    class Meta:
        model = Message
        fields = ['id', 'user_from', 'user_to', 'content', 'created_at']

class MemberListSerializer(serializers.ModelSerializer):
    owner = UserSerializer()
    user_ids = serializers.SerializerMethodField()

    def get_user_ids(self, obj):
        return ListMember.objects.filter(list=obj).values_list('user_id', flat=True)

    class Meta:
        model = List
        fields = ['id','name','description','created_at','owner','user_ids']
        read_only_fields = ['created_at','owner']

class MemberListCreateSerializer(serializers.ModelSerializer):
    user_ids = serializers.SerializerMethodField()

    def get_user_ids(self, obj):
        return ListMember.objects.filter(list=obj).values_list('user_id', flat=True)
    
    class Meta:
        model = List
        fields = ['id','name','description','created_at','owner','user_ids']
        read_only_fields = ['created_at','owner']

class MemberListDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    #list = MemberListSerializer()

    class Meta:
        model = ListMember
        fields = '__all__'
    

class PostSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    repost_count = serializers.SerializerMethodField()
    repost_user = serializers.SerializerMethodField()
    repost_created_at = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'owner', 'content', 'created_at','view_count', 'like_count','repost_count', 'repost_user', 'repost_created_at']
        read_only_fields = ['created_at','owner', 'like_count','repost_count']

    def get_like_count(self, obj):
        return Like.objects.filter(post=obj).count()
    
    def get_repost_count(self, obj):
        return Repost.objects.filter(post=obj).count()
    
    def get_repost_user(self, obj):
        if hasattr(obj, 'repost'):
            return UserSerializer(obj.repost.user).data
        return None

    def get_repost_created_at(self, obj):
        if hasattr(obj, 'repost'):
            return obj.repost.created_at
        return None
    
    def create(self, validated_data):
        content = validated_data.get('content', '')
        post = Post.objects.create(**validated_data)
  
        # リプライ対象のユーザー名を検出
        reply_usernames = re.findall(r'@(\w+)', content)

        for username in reply_usernames:
            try:
                reply_user = User.objects.get(uid=username)
                content = re.sub(f'@{username}', f'<uid>{username}</uid>', content)
                post.content = content
                Reply.objects.create(
                    post=post,
                    replier=validated_data['owner'],
                    reply_to=reply_user
                )
            except User.DoesNotExist:
                # ユーザーが存在しない場合の処理
                pass
        
        post.content = content
        post.save()
        return post
    


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['user','post']
        read_only_fields = ['user']

class FollowSerializer(serializers.ModelSerializer): #idでやり取りのみ
    class Meta:
        model = Follow
        fields = ['follower','following']
        read_only_fields = ['follower']

class FollowUserDetailSerializer(serializers.ModelSerializer): #フォロー・フォロワー一覧表示用にユーザー情報欲しい
    follower = UserSerializer()
    following = UserSerializer()

    class Meta:
        model = Follow
        fields = ['follower','following']
        read_only_fields = ['follower','following']



class CustomRegisterSerializer(RegisterSerializer):
    id = serializers.UUIDField(default=uuid.uuid4)
    email = serializers.EmailField(max_length=255)
    username = serializers.CharField(max_length=255)
    # uid = serializers.CharField(max_length=255)
    # is_active = serializers.BooleanField(default=True)
    # is_staff = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ('email','username','uid','password', 'last_login', 'superuser', 'is_active', 'is_staff', 'profile_statement' ,'avatar_imgurl')


    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        #data['username'] = self.validated_data.get('username', '')
        return data
    
    def save(self, request):
        def createRandomStr(n):
            import random, string
            randlst = [random.choice(string.ascii_letters + string.digits) for i in range(n)]
            return ''.join(randlst)
        
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        user.uid = createRandomStr(10)
        user.avatar_imgurl = "default.png"
        user.save()
        adapter.save_user(request, user, self)
        return user



#イカ、ブログ

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name')

class BlogSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    tag = TagSerializer(many=True)

    class Meta:
        model = Blog
        fields = '__all__'
        #fields = ('id', 'title', 'content', 'category', 'tag', 'created_at')

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'

