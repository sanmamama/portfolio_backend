from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.html import escape
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
        text = strip_tags(item.content_html)

        # 冒頭300文字
        excerpt = text[:300]

        if len(text) > 300:
            excerpt += "..."

        url = f"https://www.sanmamama.com/detail/{item.id}"

        return (
            f"<p>{escape(excerpt)}</p>"
            f'<p><a href="{url}">続きを読む</a></p>'
        )

    def item_link(self, item):
        return f"/detail/{item.id}/"

    def item_pubdate(self, item):
        return item.created_at