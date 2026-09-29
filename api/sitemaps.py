from django.contrib.sitemaps import Sitemap
from .models import Blog


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Blog.objects.filter(is_draft=False)

    def location(self, obj):
        return f"/blog/{obj.id}"

    def lastmod(self, obj):
        return obj.updated_at