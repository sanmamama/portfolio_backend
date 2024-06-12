from django.db import models


class User(models.Model):
    name = models.CharField(max_length=32)
    mail = models.EmailField()