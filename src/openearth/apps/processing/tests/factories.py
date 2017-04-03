from __future__ import unicode_literals
import datetime
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import models as auth_models
from openearth.apps.processing import models as processing_models


class StaffUserFactory(DjangoModelFactory):
    FACTORY_FOR = auth_models.User
    username = factory.Sequence("username{0}".format)
    first_name = factory.Sequence("first name {0}".format)
    last_name = factory.Sequence("last name {0}".format)
    email = factory.Sequence("email{0}@example.org".format)
    password = 'adm1n'
    email = 'test@test.com'
    is_staff = True
    is_active = True

    @classmethod
    def _prepare(cls, create, **kwargs):
        password = kwargs.pop('password', None)
        user = super(StaffUserFactory, cls)._prepare(create, **kwargs)
        if password:
            user.set_password(password)
            if create:
                user.save()
        return user


class AdminFactory(StaffUserFactory):
    is_superuser = True


class ProcessingJobImageFactory(DjangoModelFactory):
    FACTORY_FOR = processing_models.ProcessingJobImage
    interpreter = '/opt/python2.7/bin/python2.7 {script_path}'
    libvirt_image = factory.Sequence('image-{0}'.format)
    name = factory.Sequence('myname-{0}'.format)
    description = factory.Sequence('description-{0}'.format)


class ProcessingEnvironmentFactory(DjangoModelFactory):
    FACTORY_FOR = processing_models.ProcessingEnvironment
    author = factory.SubFactory(AdminFactory)
    libvirt_image = factory.SubFactory(ProcessingJobImageFactory)
    repo = factory.Sequence('repo-{0}'.format)
    name = factory.Sequence('name-{0}'.format)
    open_earth = True
    created_date = factory.LazyAttribute(lambda o: datetime.datetime.utcnow())


class ProcessingJobFactory(DjangoModelFactory):
    FACTORY_FOR = processing_models.ProcessingJob
    environment = factory.SubFactory(ProcessingEnvironmentFactory)
    start = factory.LazyAttribute(lambda o: datetime.datetime.utcnow())
    created_date = factory.LazyAttribute(lambda o: datetime.datetime.utcnow())
    status = processing_models.ProcessingJob.STATUS.CREATED
    auto_commit = True
    script = factory.Sequence('script-name-{0}.py'.format)
