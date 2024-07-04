from rest_framework import serializers
from .models import *
from dj_rest_auth.registration.serializers import RegisterSerializer
from allauth.account.adapter import get_adapter
import uuid



#イカ、ポスッター

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email','uid','username','avatar_imgurl', 'profile_statement' )

class PostSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    class Meta:
        model = Post
        fields = ['id', 'owner', 'content', 'created_at']
        read_only_fields = ['created_at','owner']

class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    post = PostSerializer
    class Meta:
        model = Like
        fields = '__all__'

class FollowSerializer(serializers.ModelSerializer):
    follower = UserSerializer()
    following = UserSerializer()
    class Meta:
        model = Follow
        fields = '__all__'



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

