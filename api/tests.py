from datetime import datetime, timezone
from io import BytesIO
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import Blog, Category, Tag


class BlogReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Python', description='')
        cls.other = Category.objects.create(name='Other', description='')
        cls.tag = Tag.objects.create(name='React')
        cls.second_tag = Tag.objects.create(name='API')
        cls.articles = []
        for number in range(15):
            article = Blog.objects.create(title=f'Article {number}', content='', category=cls.category if number < 7 else cls.other)
            Blog.objects.filter(pk=article.pk).update(
                created_at=datetime(2025, 1, number + 1, tzinfo=timezone.utc),
                content_html='<p>CaseSensitive &amp; body</p>' if number == 0 else '<p>本文</p>',
            )
            if number % 2 == 0:
                article.tag.add(cls.tag)
            cls.articles.append(article)
        cls.draft = Blog.objects.create(title='Draft', content='', category=cls.category, is_draft=True)

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_bounded_list_and_page_clamping(self):
        first = self.client.get('/api/blog/').json()
        self.assertEqual(first['count'], 15)
        self.assertEqual(len(first['results']), 12)
        self.assertEqual(first['results'][0]['id'], self.articles[-1].id)
        self.assertNotIn('content_html', first['results'][0])
        self.assertNotIn('toc_html', first['results'][0])
        last = self.client.get('/api/blog/?page=99').json()
        self.assertEqual(last['page'], 2)
        self.assertEqual(len(last['results']), 3)
        self.assertEqual(self.client.get('/api/blog/?page=-2').json()['page'], 1)

    def test_case_sensitive_html_search_overrides_other_filters(self):
        data = self.client.get('/api/blog/', {'q': 'CaseSensitive', 'category': 'Other'}).json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(self.client.get('/api/blog/', {'q': 'casesensitive'}).json()['count'], 0)
        self.assertEqual(self.client.get('/api/blog/', {'q': '<p>CaseSensitive'}).json()['count'], 1)

    def test_or_filters_and_reverse_tag_substring(self):
        data = self.client.get('/api/blog/', {'category': 'Python', 'tag': 'React extra'}).json()
        self.assertEqual(data['count'], 11)
        self.assertEqual(self.client.get('/api/blog/', {'tag': 'Re'}).json()['count'], 0)
        self.assertEqual(self.client.get('/api/blog/', {'category': 'Pyth'}).json()['count'], 0)

    def test_empty_results_and_invalid_month(self):
        data = self.client.get('/api/blog/?q=missing').json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertEqual(self.client.get('/api/blog/?date=202513').json()['count'], 0)

    def test_browser_timezone_month_boundary(self):
        Blog.objects.filter(pk=self.articles[0].pk).update(created_at=datetime(2025, 1, 31, 16, tzinfo=timezone.utc))
        self.assertEqual(self.client.get('/api/blog/', {'date': '202502', 'tz': 'Asia/Tokyo'}).json()['count'], 1)
        self.assertEqual(self.client.get('/api/blog/', {'date': '202502', 'tz': 'UTC'}).json()['count'], 0)
        archives = dict(self.client.get('/api/blog/summary/?tz=Asia/Tokyo').json()['archives'])
        self.assertEqual(archives, {'202501': 14, '202502': 1})

    def test_summary_uses_all_public_articles_and_id_order(self):
        data = self.client.get('/api/blog/summary/?q=missing').json()
        self.assertEqual(data['categories'], [
            [str(self.category.id), {'name': 'Python', 'count': 7}],
            [str(self.other.id), {'name': 'Other', 'count': 8}],
        ])
        self.assertEqual(data['tags'], [[str(self.tag.id), {'name': 'React', 'count': 8}]])

    def test_detail_neighbors_related_ranking_and_draft_visibility(self):
        current = self.articles[6]
        current.tag.add(self.second_tag)
        self.articles[4].tag.add(self.second_tag)
        data = self.client.get(f'/api/blog/{current.pk}/').json()
        self.assertIn('content_html', data)
        self.assertEqual(data['previous_article']['id'], self.articles[5].id)
        self.assertEqual(data['next_article']['id'], self.articles[7].id)
        self.assertEqual([obj['id'] for obj in data['related_posts']], [self.articles[4].id, self.articles[2].id, self.articles[0].id])
        self.assertEqual(self.client.get(f'/api/blog/{self.draft.pk}/').status_code, 404)
        self.assertIsNone(self.client.get(f'/api/blog/{self.articles[0].pk}/').json()['previous_article'])

    def test_excerpt_and_likes(self):
        Blog.objects.filter(pk=self.articles[-1].pk).update(content_html='<p>' + 'あ' * 101 + '&amp;</p>')
        item = self.client.get('/api/blog/').json()['results'][0]
        self.assertEqual(item['excerpt'], 'あ' * 100 + '.....')
        response = self.client.patch(f'/api/blog/{self.articles[-1].pk}/like/')
        self.assertEqual(response.json()['likes'], 1)

    def test_list_query_count_does_not_grow_per_article(self):
        # count, bounded articles with category, prefetched tags
        with self.assertNumQueries(3):
            self.client.get('/api/blog/')

    def test_same_date_neighbors_and_utf16_excerpt(self):
        first, second = self.articles[:2]
        timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        Blog.objects.filter(pk__in=[first.pk, second.pk]).update(created_at=timestamp)
        data = self.client.get(f'/api/blog/{second.pk}/').json()
        self.assertEqual(data['previous_article']['id'], first.pk)
        Blog.objects.filter(pk=self.articles[-1].pk).update(content_html='<p>' + 'a' * 99 + '😀</p>')
        item = self.client.get('/api/blog/').json()['results'][0]
        self.assertEqual(item['excerpt'], 'a' * 99 + '\ufffd.....')

    def test_summary_cache_and_edit_invalidation(self):
        expected = self.client.get('/api/blog/summary/').json()
        with self.assertNumQueries(0):
            self.assertEqual(self.client.get('/api/blog/summary/').json(), expected)
        article = self.articles[0]
        article.is_draft = True
        article.save(update_fields=['is_draft'])
        updated = self.client.get('/api/blog/summary/').json()
        self.assertEqual(updated['categories'][0][1]['count'], 6)
        article.tag.clear()
        self.other.name = 'Renamed'
        self.other.save()
        self.assertEqual(self.client.get('/api/blog/summary/').json()['categories'][1][1]['name'], 'Renamed')
        article.delete()
        self.assertEqual(self.client.get('/api/blog/summary/').status_code, 200)

    def test_detail_queries_exclude_unused_bodies(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as queries:
            data = self.client.get(f'/api/blog/{self.articles[6].pk}/').json()
        self.assertEqual(set(data['related_posts'][0]), {'id', 'title', 'img', 'thumbnail'})
        body_reads = [query for query in queries if '"content_html"' in query['sql']]
        self.assertEqual(len(body_reads), 1)

    def test_likes_skip_rendering_and_keep_article_modification_time(self):
        article = Blog.objects.get(pk=self.articles[0].pk)
        with patch.object(Blog, 'render_content', side_effect=AssertionError('Unexpected render')):
            with self.assertNumQueries(4):  # transaction savepoint, update, read, release
                self.assertEqual(self.client.patch(f'/api/blog/{article.pk}/like/').json()['likes'], 1)
            self.assertEqual(self.client.patch(f'/api/blog/{article.pk}/like/').json()['likes'], 2)
        article.refresh_from_db()
        self.assertEqual(article.content_html, '<p>CaseSensitive &amp; body</p>')
        before = article.updated_at
        self.client.patch(f'/api/blog/{article.pk}/like/')
        article.refresh_from_db()
        self.assertEqual(article.updated_at, before)
        self.assertEqual(self.client.patch(f'/api/blog/{self.draft.pk}/like/').status_code, 404)

    def test_render_content_only_for_body_edits(self):
        article = Blog.objects.get(pk=self.articles[0].pk)
        with patch.object(Blog, 'render_content', side_effect=AssertionError('Unexpected render')):
            article.likes += 1
            article.save(update_fields=['likes'])
            article.title = 'Renamed'
            article.save()
        article.content = '# Heading\n\n:::answer\nAnswer\n:::\n\n![img](/test.png)'
        article.save(update_fields=['content'])
        article.refresh_from_db()
        self.assertIn('answer-box', article.content_html)
        self.assertIn('img-fluid', article.content_html)
        self.assertIn('anchor', article.content_html)
        self.assertIn('Heading', article.toc_html)

    def test_thumbnail_preserves_alpha_and_does_not_regenerate(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            source = BytesIO()
            Image.new('RGBA', (800, 400), (0, 0, 255, 128)).save(source, format='PNG')
            article = Blog.objects.create(title='Image', content='', category=self.category,
                img=SimpleUploadedFile('test.png', source.getvalue(), content_type='image/png'))
            with article.thumbnail.open('rb') as file, Image.open(file) as thumbnail:
                self.assertEqual(thumbnail.size, (400, 200))
                self.assertIn('A', thumbnail.getbands())
            name = article.thumbnail.name
            article.title = 'New title'
            article.save()
            self.assertEqual(article.thumbnail.name, name)

    def test_legacy_all_is_compatible_and_deprecated(self):
        response = self.client.get('/api/blog/all/')
        self.assertEqual(response['Deprecation'], 'true')
        self.assertEqual(len(response.json()), 15)

    def test_explain_command_runs_on_existing_database(self):
        output = StringIO()
        call_command('explain_blog', q='React', stdout=output)
        self.assertTrue(output.getvalue().strip())
