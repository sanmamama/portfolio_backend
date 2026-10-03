"""Concurrency regression test requiring the dedicated PostgreSQL settings."""
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from .models import Blog, Category


@skipUnless(connection.vendor == 'postgresql', 'Requires isolated PostgreSQL test database')
class BlogConcurrentLikeTests(TransactionTestCase):
    def test_parallel_likes_are_not_lost(self):
        category = Category.objects.create(name='Test', description='')
        article = Blog.objects.create(title='Test', content='', category=category)

        def like(_):
            try:
                response = APIClient().patch(f'/api/blog/{article.pk}/like/')
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(like, range(12))), [200] * 12)
        article.refresh_from_db()
        self.assertEqual(article.likes, 12)
