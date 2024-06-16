from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField



#これはテストのため

class User(models.Model):
    name = models.CharField(max_length=32)
    mail = models.EmailField()

    def __str__(self):
        return self.name


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
	category_id = models.ForeignKey('Category', on_delete=models.CASCADE)
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