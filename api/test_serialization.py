import json
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework.renderers import JSONRenderer

from .models import Follow, Like, List, ListMember, Message, Notification, Post, Repost, User
from .serializer import (
    FollowUserDetailSerializer, MemberListDetailSerializer, MemberListSerializer,
    MessageUserListSerializer, NotificationSerializer, PostSerializer, UserSerializer,
)
from .serialization_queries import prepare_response


class ResponseQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [User.objects.create_user(
            email=f'user{number}@example.com', uid=f'user{number}', username=f'User {number}',
            avatar_imgurl='avatar.png',
        ) for number in range(7)]
        cls.posts = [Post.objects.create(owner=user, content=f'post {number}')
                     for number, user in enumerate(cls.users)]
        cls.reply = Post.objects.create(owner=cls.users[1], content='reply', parent=cls.posts[0])
        for number in range(6):
            Follow.objects.create(follower=cls.users[number], following=cls.users[number + 1])
            Like.objects.create(user=cls.users[number + 1], post=cls.posts[number])
            Repost.objects.create(user=cls.users[number + 1], post=cls.posts[number])
        # Duplicates currently allowed by the schema must remain in counts/arrays.
        Like.objects.create(user=cls.users[1], post=cls.posts[0])
        cls.member_list = List.objects.create(name='Friends', owner=cls.users[0])
        for user in cls.users:
            ListMember.objects.create(list=cls.member_list, user=user)
        cls.message = Message.objects.create(user_from=cls.users[0], user_to=cls.users[1], content='message')
        Notification.objects.create(sender=cls.users[0], receiver=cls.users[1],
                                    post=cls.posts[0], message=cls.message, notification_type='mention')

    def serialize(self, serializer, queryset, optimized=True):
        # Disabling preparation exercises the original per-object query methods.
        with patch('api.serializer.prepare_response', side_effect=prepare_response if optimized else lambda instances: None):
            with CaptureQueriesContext(connection) as queries:
                # Compare the actual JSON, including lazily evaluated user_ids.
                data = json.loads(JSONRenderer().render(serializer(queryset(), many=True).data))
        return data, len(queries)

    def test_post_payload_is_identical_and_query_count_is_bounded(self):
        queryset = lambda: Post.objects.filter(pk__in=[post.pk for post in self.posts[:6]]).order_by('pk')
        original, before = self.serialize(PostSerializer, queryset, optimized=False)
        actual, after = self.serialize(PostSerializer, queryset)
        self.assertEqual(actual, original)
        self.assertEqual(actual[0]['like_count'], 2)
        self.assertEqual(actual[0]['reply_count'], 1)
        self.assertEqual(after, 9)
        self.assertGreater(before, after * 4)
        print(f'PostSerializer (6 posts): {before} -> {after} queries')

    def test_post_queries_do_not_increase_with_page_size(self):
        _, single = self.serialize(PostSerializer, lambda: Post.objects.filter(pk=self.posts[0].pk))
        _, several = self.serialize(PostSerializer, lambda: Post.objects.filter(pk__in=[post.pk for post in self.posts]))
        self.assertEqual(single, several)

    def test_user_payload_and_duplicates_are_preserved(self):
        queryset = lambda: User.objects.all().order_by('pk')
        expected, before = self.serialize(UserSerializer, queryset, optimized=False)
        actual, after = self.serialize(UserSerializer, queryset)
        self.assertEqual(actual, expected)
        self.assertEqual(after, 5)
        self.assertEqual(actual[1]['like'], [self.posts[0].pk, self.posts[0].pk])
        self.assertGreater(before, after)

    def test_nested_response_payloads_are_preserved(self):
        for serializer, model in (
            (MessageUserListSerializer, Message), (NotificationSerializer, Notification),
            (MemberListSerializer, List), (MemberListDetailSerializer, ListMember),
            (FollowUserDetailSerializer, Follow),
        ):
            with self.subTest(serializer=serializer.__name__):
                queryset = lambda: model.objects.all().order_by('pk')
                expected, before = self.serialize(serializer, queryset, optimized=False)
                actual, after = self.serialize(serializer, queryset)
                self.assertEqual(actual, expected)
                self.assertLess(after, before)

    def test_dynamic_repost_owner_and_timestamp_are_preserved(self):
        def queryset():
            posts = list(Post.objects.filter(pk__in=[post.pk for post in self.posts[:3]]).order_by('pk'))
            reposts = {obj.post_id: obj for obj in Repost.objects.filter(post_id__in=[post.pk for post in posts])}
            for post in posts:
                post.repost = reposts[post.pk]
            return posts
        expected, before = self.serialize(PostSerializer, queryset, optimized=False)
        actual, after = self.serialize(PostSerializer, queryset)
        self.assertEqual(actual, expected)
        self.assertEqual(actual[0]['repost_user']['id'], self.users[1].pk)
        self.assertIsNotNone(actual[0]['repost_created_at'])
        self.assertLess(after, before)

    def test_empty_response_performs_no_queries(self):
        with self.assertNumQueries(0):
            self.assertEqual(PostSerializer([], many=True).data, [])

    def test_new_serialization_refreshes_counts_after_writes(self):
        user = User.objects.get(pk=self.users[0].pk)
        before = UserSerializer(user).data['post_count']
        Post.objects.create(owner=user, content='new')
        self.assertEqual(UserSerializer(user).data['post_count'], before + 1)

    def test_authenticated_timeline_still_returns_six_posts(self):
        client = APIClient()
        client.force_authenticate(user=self.users[0])
        with patch('api.serializer.prepare_response', side_effect=lambda instances: None):
            with CaptureQueriesContext(connection) as original_queries:
                original = client.get('/api/postter/post/')
        # Reading the timeline increments view counters in the existing API.
        Post.objects.update(view_count=0)
        with CaptureQueriesContext(connection) as queries:
            response = client.get('/api/postter/post/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), original.json())
        self.assertEqual(len(response.json()['results']), 6)
        self.assertLessEqual(len(queries), 14)
        print(f'Timeline API (6 posts): {len(original_queries)} -> {len(queries)} queries')
