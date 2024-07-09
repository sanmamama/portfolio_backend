from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser,  PermissionsMixin
import uuid

#postter
class Reply(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE)
    replier = models.ForeignKey('User', related_name='replies', on_delete=models.CASCADE)
    reply_to = models.ForeignKey('User', related_name='replied_to', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Follow(models.Model):
    follower = models.ForeignKey('User', related_name='follower', on_delete=models.CASCADE)
    following = models.ForeignKey('User', related_name='following', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Post(models.Model):
    owner = models.ForeignKey('User', verbose_name='オーナー', on_delete=models.CASCADE)
    content = models.TextField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class Like(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class List(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class ListMember(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    list = models.ForeignKey('List', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    user_from = models.ForeignKey('User',related_name='messages_sent', on_delete=models.CASCADE)
    user_to = models.ForeignKey('User',related_name='messages_received', on_delete=models.CASCADE)
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        #user.username = email.split('@')[0]
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    #id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    uid = models.CharField(max_length=255,unique=True)
    avatar_imgurl = models.ImageField(blank=True)
    profile_statement = models.CharField(max_length=255,blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email


#ブログアプリ

class Tag(models.Model):
    name = models.CharField('タグ', max_length=50)

    def __str__(self):
        return self.name
	
class Blog(models.Model):
	title = models.CharField(max_length=100)
	content = RichTextUploadingField()
	img = models.ImageField(upload_to='media/')
	created_at = models.DateTimeField()
	updated_at = models.DateTimeField()
	category = models.ForeignKey('Category', on_delete=models.CASCADE)
	tag = models.ManyToManyField(Tag,blank=True, null=True)
	likes = models.PositiveIntegerField(default=0)
	def __str__(self):
		return self.title

class Comment(models.Model):
	post_id = models.ForeignKey('Blog', on_delete=models.CASCADE ,related_name='comments')
	name = models.CharField(max_length=100)
	body = models.CharField(max_length=1000)
	created_at = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return self.body

class Category(models.Model):
	name = models.CharField(max_length=100)
	description = models.CharField(max_length=100)
	created_at = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return self.name


class Contact(models.Model):
    name = models.CharField(max_length=100, verbose_name='お名前')
    email = models.EmailField(verbose_name='メールアドレス')
    message = models.TextField(verbose_name='メッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日')

    def __str__(self):
        return self.name