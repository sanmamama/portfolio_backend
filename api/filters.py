import django_filters
from .models import Blog


#イカ、ブログ

class BlogFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    tag = django_filters.CharFilter(field_name='tag__name', lookup_expr='icontains')
    date = django_filters.CharFilter(method='filter_by_date')

    class Meta:
        model = Blog
        fields = ['category','tag','date']

    def filter_by_date(self, queryset, name, value):
        if len(value) == 6 and value.isdigit():
            year = int(value[:4])
            month = int(value[4:6])
            return queryset.filter(created_at__year=year, created_at__month=month)
        return queryset
