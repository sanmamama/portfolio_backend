"""Inspect real PostgreSQL plans before choosing schema changes."""
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand

from api.blog_views import filter_public_blogs
from api.models import Blog


class Command(BaseCommand):
    help = 'Print the bounded public blog query plan without changing data.'

    def add_arguments(self, parser):
        for name in ('q', 'category', 'tag', 'date'):
            parser.add_argument(f'--{name}', default='')
        parser.add_argument('--tz', default='Asia/Tokyo')

    def handle(self, **options):
        queryset = filter_public_blogs(
            Blog.objects.filter(is_draft=False).select_related('category').defer('content', 'toc_html'),
            options, ZoneInfo(options['tz'])
        ).order_by('-created_at', 'id')[:12]
        self.stdout.write(queryset.explain())
