from django.db import models


class DummyModel(models.Model):
    reference_id = models.IntegerField()