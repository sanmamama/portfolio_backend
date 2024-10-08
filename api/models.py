from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser,  PermissionsMixin
from markdownx.models import MarkdownxField
import uuid

#postter



class Mention(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE)
    user_from = models.ForeignKey('User', related_name='mention_user_from', on_delete=models.CASCADE)
    user_to = models.ForeignKey('User', related_name='mention_user_to', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Follow(models.Model):
    follower = models.ForeignKey('User', related_name='follower', on_delete=models.CASCADE)
    following = models.ForeignKey('User', related_name='following', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Post(models.Model):
    owner = models.ForeignKey('User', on_delete=models.CASCADE)
    content = models.TextField(max_length=140)
    content_EN = models.TextField(null=True, blank=True)
    content_JA = models.TextField(null=True, blank=True)
    content_ZH = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='reply', on_delete=models.CASCADE)


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
    content_EN = models.TextField(null=True, blank=True)
    content_JA = models.TextField(null=True, blank=True)
    content_ZH = models.TextField(null=True, blank=True)
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
    LOCALE_CHOICES = [
        ('en', 'English'),
        ('ja', 'Japanese'),
        ('zh', 'Chinese'),
    ]

    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    uid = models.CharField(max_length=255,unique=True)
    avatar_imgurl = models.ImageField(blank=True)
    profile_statement = models.CharField(max_length=255,blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    locale = models.CharField(max_length=5,choices=LOCALE_CHOICES,default='ja',)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
    
    
class Repost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')




class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('follow', 'Follow'),
        ('like', 'Like'),
        ('repost', 'Repost'),
        ('mention', 'Mention'),
        ('message', 'Message'),
        ('reply', 'Reply'),
        ('custom', 'Custom Event'),
    ]

    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES) 
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True) 
    post = models.ForeignKey('Post',related_name='post', null=True, blank=True, on_delete=models.CASCADE)
    message = models.ForeignKey('Message',related_name='Message', null=True, blank=True, on_delete=models.CASCADE)
    parent = models.ForeignKey('Post',related_name='related_post', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.sender} {self.get_notification_type_display()} {self.receiver}'


#ブログアプリ

class Book(models.Model):
    STATUS_CHOICES = [
        ('読書中', '読書中'),
        ('読了', '読了'),
        ('積読', '積読')
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    genre = models.CharField(max_length=100, blank=True, null=True)
    rating = models.PositiveSmallIntegerField(blank=True, null=True)
    read_date = models.DateField(null=True, blank=True)
    review = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='reading')
    isbn = models.CharField(max_length=13)

    class Meta:
        ordering = ['-read_date']

class Tag(models.Model):
    name = models.CharField('タグ', max_length=50)

    def __str__(self):
        return self.name
	
class Blog(models.Model):
    title = models.CharField(max_length=100)
    content = MarkdownxField()
    img = models.ImageField(upload_to='media/')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    tag = models.ManyToManyField(Tag,blank=True)
    likes = models.PositiveIntegerField(default=0)
    is_draft = models.BooleanField(default=False)
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