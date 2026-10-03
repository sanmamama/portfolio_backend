"""Prepare only the response objects, without changing the API's fields."""
from collections import defaultdict

from django.db.models import Count, Q, prefetch_related_objects

from .models import Follow, Like, List, ListMember, Message, Notification, Post, Repost, User


def prepare_response(objects):
    groups = defaultdict(list)
    seen = set()
    pending = list(objects)
    while pending:
        current = defaultdict(list)
        for obj in pending:
            # Distinct ORM instances of the same row may carry different reposts.
            if id(obj) not in seen:
                seen.add(id(obj))
                current[type(obj)].append(obj)
                groups[type(obj)].append(obj)
        pending = []
        relations = {
            Post: ('owner',), Message: ('user_from', 'user_to'),
            Notification: ('sender', 'receiver', 'post', 'message'),
            List: ('owner',), ListMember: ('user',), Follow: ('follower', 'following'),
            Repost: ('user',),
        }
        for model, instances in current.items():
            if model in relations:
                prefetch_related_objects(instances, *relations[model])
                for obj in instances:
                    pending.extend(value for name in relations[model]
                                   if (value := getattr(obj, name)) is not None)
            if model is Post:
                pending.extend(obj.repost for obj in instances if hasattr(obj, 'repost'))

    users = groups[User]
    if users:
        ids = {user.pk for user in users}
        stats = {pk: {'post_count': 0, 'following': [], 'follower': [], 'like': [], 'repost': []} for pk in ids}
        for row in Post.objects.filter(owner_id__in=ids).values('owner_id').annotate(total=Count('id')):
            stats[row['owner_id']]['post_count'] = row['total']
        for follower, following in Follow.objects.filter(
            Q(follower_id__in=ids) | Q(following_id__in=ids)
        ).order_by('pk').values_list('follower_id', 'following_id'):
            if follower in stats:
                stats[follower]['following'].append(following)
            if following in stats:
                stats[following]['follower'].append(follower)
        for model, field in ((Like, 'like'), (Repost, 'repost')):
            for user_id, post_id in model.objects.filter(user_id__in=ids).order_by('pk').values_list('user_id', 'post_id'):
                stats[user_id][field].append(post_id)
        for user in users:
            user._response_stats = stats[user.pk]

    posts = groups[Post]
    if posts:
        ids = {post.pk for post in posts}
        stats = {pk: {'like_count': 0, 'repost_count': 0, 'reply_count': 0} for pk in ids}
        for model, relation, name in (
            (Like, 'post_id', 'like_count'), (Repost, 'post_id', 'repost_count'),
            (Post, 'parent_id', 'reply_count'),
        ):
            for row in model.objects.filter(**{f'{relation}__in': ids}).values(relation).annotate(total=Count('id')):
                stats[row[relation]][name] = row['total']
        for post in posts:
            post._response_stats = stats[post.pk]

    lists = groups[List]
    if lists:
        members = defaultdict(list)
        for list_id, user_id in ListMember.objects.filter(list_id__in={obj.pk for obj in lists}).order_by('pk').values_list('list_id', 'user_id'):
            members[list_id].append(user_id)
        for obj in lists:
            obj._response_user_ids = members[obj.pk]
