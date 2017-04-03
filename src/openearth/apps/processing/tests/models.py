from __future__ import unicode_literals
from django.test import TestCase, RequestFactory
from openearth.apps.processing.tests import factories



class JobModelTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def admin_request(self, job):
        """
        Creates a request object with a logged in admin user
        """
        admin_user = factories.AdminFactory()
        request = self.factory.get('/ws/{0}'.format(job.uuid))
        request.user = admin_user
        return request

    def test_start_job(self):
        """
        Tests start_job method
        """
        # require factoryboy
        # job heeft ook een stared_by/owner user nodig.
        job = factories.ProcessingJobFactory()
        request = self.admin_request(job)
        # request heeft niet het goede path
        job.start_job()
        print job.environment.get_repo_url()
        print job.script
