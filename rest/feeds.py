from django.contrib.syndication.views import Feed
from django.urls import reverse
from api.models import Blog


class LatestBlogFeed(Feed):
    title = "さんまの技術ブログ"
    link = "/"
    description = "さんまの技術ブログの新着記事を配信します。"

    def items(self):
        return (
            Blog.objects
            .filter(is_draft=False)
            .order_by("-created_at")[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # RSS本文としてHTMLをそのまま配信
        return item.content_html

    def item_link(self, item):
        return f"/blog/{item.id}/"

    def item_pubdate(self, item):
        return item.created_at