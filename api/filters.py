import django_filters
from .models import Blog

class BlogFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    tag = django_filters.CharFilter(field_name='tag__name', lookup_expr='icontains')
    month = django_filters.NumberFilter(field_name='created_at', lookup_expr='month')

    class Meta:
        model = Blog
        fields = ['category', 'tag', 'month']