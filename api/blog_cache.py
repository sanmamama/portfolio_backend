"""Short-lived sidebar cache; each worker also expires entries after 30 seconds."""
from uuid import uuid4

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save

from .models import Blog, Category, Tag


def invalidate_summary(**kwargs):
    def invalidate():
        cache.set('blog-summary-version', uuid4().hex, timeout=None)
    invalidate()
    transaction.on_commit(invalidate)


def connect_signals():
    for model in (Blog, Category, Tag):
        for signal in (post_save, post_delete):
            signal.connect(invalidate_summary, sender=model,
                           dispatch_uid=f'blog-summary-{model.__name__}-{id(signal)}')
    m2m_changed.connect(invalidate_summary, sender=Blog.tag.through,
                        dispatch_uid='blog-summary-tags')
