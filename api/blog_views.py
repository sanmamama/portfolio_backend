"""Bounded blog reads, retaining the public site's filtering and ordering rules."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, Q, Value, When
from django.db.models.functions import StrIndex, TruncMonth
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Blog, Category, Tag
from .serializer import BlogSerializer, BlogListSerializer


def browser_timezone(request):
    try:
        return ZoneInfo(request.query_params.get('tz') or settings.TIME_ZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(settings.TIME_ZONE)


def filter_public_blogs(queryset, params, timezone):
    query = params.get('q', '')
    if query:
        # JS String.includes is case-sensitive and searches rendered HTML.
        queryset = queryset.alias(
            title_match=StrIndex('title', Value(query)),
            body_match=StrIndex('content_html', Value(query)),
            category_match=StrIndex('category__name', Value(query)),
            tag_match=StrIndex('tag__name', Value(query)),
        )
        return queryset.filter(
            Q(title_match__gt=0) | Q(body_match__gt=0)
            | Q(category_match__gt=0) | Q(tag_match__gt=0)
        ).distinct()

    category, tag, month = (params.get(key, '') for key in ('category', 'tag', 'date'))
    if not (category or tag or month):
        return queryset
    # Also preserve empty-name matches when another filter is selected.
    condition = Q(category__name=category)
    # Preserve selectedTag.includes(tag.name), including partial tag names.
    queryset = queryset.alias(selected_tag_match=StrIndex(Value(tag), F('tag__name')))
    condition |= Q(selected_tag_match__gt=0)
    if re.fullmatch(r'\d{6}', month):
        try:
            year, number = int(month[:4]), int(month[4:])
            start = datetime(year, number, 1, tzinfo=timezone)
            end = datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=timezone)
            condition |= Q(created_at__gte=start, created_at__lt=end)
        except ValueError:
            pass
    return queryset.filter(condition).distinct()


class BlogFilterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogSerializer
    queryset = Blog.objects.filter(is_draft=False).select_related('category').prefetch_related('tag')

    def list(self, request, *args, **kwargs):
        queryset = filter_public_blogs(self.get_queryset(), request.query_params, browser_timezone(request))
        paginator = Paginator(queryset.order_by('-created_at', 'id'), 12)
        # Match parseInt followed by clamping to the first/last available page.
        match = re.match(r'^\s*([+-]?\d+)', request.query_params.get('page', '1'))
        requested = int(match.group(1)) if match else 1
        page = paginator.page(min(max(requested, 1), paginator.num_pages))
        return Response({
            'count': paginator.count, 'page': page.number, 'page_count': paginator.num_pages,
            'results': BlogListSerializer(page.object_list, many=True, context=self.get_serializer_context()).data,
        })

    def retrieve(self, request, *args, **kwargs):
        article = self.get_object()
        queryset = self.get_queryset().exclude(pk=article.pk)
        previous = queryset.filter(
            Q(created_at__lt=article.created_at) | Q(created_at=article.created_at, id__lt=article.id)
        ).order_by('-created_at', '-id').first()
        following = queryset.filter(
            Q(created_at__gt=article.created_at) | Q(created_at=article.created_at, id__gt=article.id)
        ).order_by('created_at', 'id').first()
        related = queryset.annotate(
            shared_tags=Count('tag', filter=Q(tag__in=article.tag.all()), distinct=True),
        ).filter(Q(shared_tags__gt=0) | Q(category_id=article.category_id)).alias(
            same_category=Case(
                When(category_id=article.category_id, then=Value(1)),
                default=Value(0),
            )
        ).order_by('-shared_tags', '-same_category', '-created_at', 'id')[:3]
        data = dict(self.get_serializer(article).data)
        def reference(obj):
            return {'id': obj.id, 'title': obj.title} if obj else None
        data.update(previous_article=reference(previous), next_article=reference(following),
                    related_posts=BlogListSerializer(related, many=True, context=self.get_serializer_context()).data)
        return Response(data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        categories = Category.objects.filter(blog__is_draft=False).annotate(count=Count('blog')).order_by('id')
        tags = Tag.objects.filter(blog__is_draft=False).annotate(count=Count('blog')).order_by('id')
        months = self.get_queryset().order_by().annotate(
            month=TruncMonth('created_at', tzinfo=browser_timezone(request))
        ).values('month').annotate(count=Count('id')).order_by('month')
        return Response({
            'categories': [[str(obj.id), {'name': obj.name, 'count': obj.count}] for obj in categories],
            'tags': [[str(obj.id), {'name': obj.name, 'count': obj.count}] for obj in tags],
            'archives': [[obj['month'].strftime('%Y%m'), obj['count']] for obj in months],
        })

    @action(detail=False, methods=['get'])
    def all(self, request):
        # Compatibility for callers of the old API during deployment.
        return Response(self.get_serializer(self.get_queryset().order_by('-created_at', 'id'), many=True).data)
