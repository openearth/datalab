from django.db import models


class Disk(models.Model):
    # The actual model isn't used for anything, this is just to trick the Django
    # admin into displaying an admin for the system/disk model
    # The fields below are how the `system.utils` functions returm them
    name = models.CharField(max_length=256)
    size = models.IntegerField('Disk size in bytes')
    free = models.IntegerField('Free space in bytes')
    reserved = models.IntegerField('Reserved space in bytes')

