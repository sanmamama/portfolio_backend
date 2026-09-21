from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser,  PermissionsMixin
from markdownx.models import MarkdownxField
import uuid
import markdown
import re

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
    buy_date = models.DateField(null=True, blank=True)
    read_date = models.DateField(null=True, blank=True)
    review = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='reading')
    isbn = models.CharField(max_length=13)

    class Meta:
        ordering = ['-read_date']

    def __str__(self):
        return self.title

class Tag(models.Model):
    name = models.CharField('タグ', max_length=50)

    def __str__(self):
        return self.name
	

import os
import uuid
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile

def blog_image_upload_to(instance, filename):
    # 元ファイルの拡張子を取得
    ext = os.path.splitext(filename)[1].lower()

    # UUIDをファイル名として使用
    return f'blog/{uuid.uuid4().hex}{ext}'

class Blog(models.Model):
    title = models.CharField(max_length=100)
    content = MarkdownxField()
    img = models.ImageField(upload_to=blog_image_upload_to, blank=True, default='no_image.png')
    thumbnail = models.ImageField(
        upload_to='blog/thumbnails/',
        blank=True,
        default='',
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    tag = models.ManyToManyField(Tag,blank=True)
    likes = models.PositiveIntegerField(default=0)
    is_draft = models.BooleanField(default=False)
    content_html = models.TextField(blank=True)
    toc_html = models.TextField(blank=True)
    def __str__(self):
        return self.title
    
    def generate_thumbnail(self, using=None):
        # 画像なし・デフォルト画像の場合はサムネイルを使用しない
        if not self.img or self.img.name == 'no_image.png':
            if self.thumbnail:
                self.thumbnail = ''
                return True
            return False

        # 新しいファイルがアップロードされたか
        image_changed = not self.img._committed

        # 保存済み画像のパスが変更された場合も検知する
        if self.pk and not image_changed:
            old_img = (
                type(self).objects.using(using or self._state.db)
                .filter(pk=self.pk)
                .values_list('img', flat=True)
                .first()
            )
            image_changed = old_img != self.img.name

        # 画像に変更がなく、サムネイルもあれば再生成しない
        if not image_changed and self.thumbnail:
            return False

        # 元ファイルを読み取り、アップロード用の読み取り位置を戻す
        self.img.open('rb')
        try:
            source_bytes = self.img.read()
        finally:
            self.img.seek(0)

        with Image.open(BytesIO(source_bytes)) as source:
            # スマートフォン写真などの回転情報を反映
            image = ImageOps.exif_transpose(source)

            # 透過情報を維持してWebP対応の形式に変換
            if 'A' in image.getbands() or 'transparency' in image.info:
                image = image.convert('RGBA')
            else:
                image = image.convert('RGB')

            # 横幅だけを最大400pxに制限。小さい画像は拡大しない
            if image.width > 400:
                height = max(1, round(image.height * 400 / image.width))
                image = image.resize(
                    (400, height),
                    Image.Resampling.LANCZOS
                )

            with BytesIO() as output:
                image.save(
                    output,
                    format='WEBP',
                    quality=80,
                    method=6
                )

                self.thumbnail.save(
                    f'{uuid.uuid4().hex}.webp',
                    ContentFile(output.getvalue()),
                    save=False
                )

        return True
    
    def save(self, *args, **kwargs):

        update_fields = kwargs.get('update_fields')

        if update_fields is not None:
            update_fields = set(update_fields)

            # Djangoの「何も更新しない」という指定を維持
            if not update_fields:
                return

            kwargs['update_fields'] = update_fields

        # 通常保存、または画像を更新する部分保存の場合に実行
        if update_fields is None or 'img' in update_fields:
            thumbnail_changed = self.generate_thumbnail(
                using=kwargs.get('using')
            )

            if thumbnail_changed and update_fields is not None:
                update_fields.add('thumbnail')

        # 本文だけを部分更新する場合も、生成したHTMLを保存する
        if update_fields is not None and 'content' in update_fields:
            update_fields.update({'content_html', 'toc_html'})

        md = markdown.Markdown(
            extensions=['toc']
        )

        # :::answer ～ ::: を <details> に変換
        def replace_answer(match):
            answer_content = match.group(1).strip()

            answer_md = markdown.Markdown()
            answer_html = answer_md.convert(answer_content)

            return f'''
<details class="answer-box">
<summary>答えを見る</summary>
<div class="answer-content">
{answer_html}
</div>
</details>
    '''

        content = re.sub(
            r':::answer\s*(.*?)\s*:::',
            replace_answer,
            self.content,
            flags=re.DOTALL
        )

        html = md.convert(content)

        counter = {'h_tag': 0}

        def replace_h_tag(match):
            counter['h_tag'] += 1

            if counter['h_tag'] == 1:
                return f'{match.group(1)} class="anchor mt-1 mb-1 pt-0 pb-0" {match.group(2)}'

            return f'{match.group(1)} class="anchor mt-5 mb-0 pt-0 pb-0" {match.group(2)}'

        html = re.sub(
            r'(<h[1-7])(.*?>)',
            replace_h_tag,
            html
        )

        html = re.sub(
            r'(</h[1-7]>)',
            r'\1<hr class="mt-3 mb-3"/>',
            html
        )

        html = re.sub(
            r'(<img.*?)(/>)',
            r'\1 class="img-fluid" />',
            html
        )

        self.content_html = html
        self.toc_html = md.toc

        super().save(*args, **kwargs) 


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