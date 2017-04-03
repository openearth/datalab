from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User

'''
File: openearth.models
door: robert Los
datum: 22-1-2014
doel: generieke openearth classes
'''


class FileType(models.Model):
    """
    Een lijst van ondersteunde bestandsformaten
    """
    filetype = models.CharField(max_length=40L, null=False, blank=False)
    file_extension = models.CharField(max_length=10L, null=False, blank=False)
    description = models.TextField(blank=True, null=False)

    class Meta:
        abstract = True
    def __unicode__(self):
        return self.filetype


class PhysicalFile(models.Model):
    title = models.CharField(max_length=128L, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, blank=False, null=False)
    related_filename = models.CharField(max_length=255L, null=False, blank=True)
    owner = models.ForeignKey(User, blank=True, null=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.title


class PhysicalFolder(models.Model):
    title = models.CharField(max_length=128L, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, blank=False, null=False)
    folder_name = models.CharField(max_length=255L, null=False, blank=True)
    owner = models.ForeignKey(User, blank=True, null=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.title


class FileStatus(models.Model):
    status = models.CharField(max_length=40L, null=False, blank=True)
    sequence = models.IntegerField(null=False, blank=True)

    class Meta:
        verbose_name_plural = "stati"
        abstract = True

    def __unicode__(self):
        return self.status
