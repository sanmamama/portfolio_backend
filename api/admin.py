from django.contrib import admin
from .models import *
from markdownx.admin import MarkdownxModelAdmin
#from ckeditor_uploader.widgets import CKEditorUploadingWidget
#from django import forms

"""
class PostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        model = Blog
        fields = '__all__'

class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
"""


admin.site.register(Blog, MarkdownxModelAdmin)
admin.site.register(Tag)
admin.site.register(Comment)
admin.site.register(Category)
admin.site.register(Contact)