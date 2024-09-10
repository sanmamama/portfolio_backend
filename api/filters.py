import django_filters
from .models import Blog
from django.db.models import Q

#イカ、ブログ

class BlogFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    tag = django_filters.CharFilter(field_name='tag__name', lookup_expr='icontains')
    date = django_filters.CharFilter(method='filter_by_date')
    q = django_filters.CharFilter(method='filter_by_all_fields')

    class Meta:
        model = Blog
        fields = ['category','tag','date','q']

    def filter_by_date(self, queryset, name, value):
        if len(value) == 6 and value.isdigit():
            year = int(value[:4])
            month = int(value[4:6])
            return queryset.filter(created_at__year=year, created_at__month=month)
        return queryset
    
    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(category__name__icontains=value) |
            Q(tag__name__icontains=value) |
            Q(title__icontains=value) |
            Q(content__icontains=value)
        )
