from __future__ import unicode_literals
from django.core.validators import validate_ipv46_address
from django.test.utils import override_settings
import libvirt
import logging
import os
import mock
import multiprocessing
import shutil
import time
from uuid import uuid1
import re
from pandas.tslib import Timestamp
from subprocess import Popen
from ..container import LibVirtDomain
from openearth.apps.processing.tests import factories as processing_factories
from . import factories as script_exec_factories
from ..task_utils import wait_for_ip, cleanup, find_files, add_file_to_job_result, \
    create_results_dir
from openearth.apps.script_execution_manager.models import Observation
from openearth.apps.script_execution_manager.tasks import run_script, commit, \
    setup_logger
from openearth.apps.script_execution_manager.tests import LibVirtTest, \
    LibVirtTestMixin

logger = logging.getLogger(__name__)


class TestRunScriptTask(LibVirtTestMixin):
    test_results_data_dir = '/tmp/results'
    instances_running = []

    def tearDown(self):
        super(TestRunScriptTask, self).tearDown()
        re_nc_files = re.compile(r"^.*nc$")
        for path in os.listdir(self.test_results_data_dir):
            if re_nc_files.match(path):
                logger.info('Removing demo files: {0} '.format(path))
                os.remove(os.path.join(self.test_results_data_dir, path))


        vir_connect_obj = libvirt.open('lxc:///')
        for inst in self.instances_running:
            logger.info('Destroying potentially running domain: "{0}"'.format(inst))
            try:
                domain = vir_connect_obj.lookupByName(inst)
                domain.destroy()
            except libvirt.libvirtError, e:
                logger.warn(unicode(e))

            logger.info('Removing "{0}" image'.format(inst))
            container_path = '/data/containers/{0}'.format(inst)
            if os.path.exists(container_path):
                os.remove(container_path)

    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.image_base_dir = os.path.join(cls.test_data_dir, 'containers')

    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_wait_for_ip(self):
        """
        Tests if dnmasq.leases is parsed when written to and if it returns IP.

        This test creates a thread from function "write_change". Then it calls
        wait_for_ip, which monitors dnmasq.leases. wait_for_ip should return a
        valid ip if the line in write_change is written to that file.

        The thread "write_change" dies after 2 seconds.
        """
        lv = LibVirtDomain(uuid=uuid1(), image='centos-6-x86_64', driver_uri='lxc:///')
        lv.dnsmasq_leases = os.path.join(self.test_data_dir, 'default.leases')
        lv._network_mac_address = "00:16:3e:46:ae:51"

        def write_change(fname):
            """
            Write to file after 2 seconds in seperate thread.
            """
            logger.info('Will modify file in 2 seconds.')
            time.sleep(2)
            with open(fname, 'w') as fp:
                logger.info('Modify file "{0}" now.'.format(fname))
                fp.writelines('1393849324 00:16:3e:46:ae:51 192.168.122.246 * *')

        p = multiprocessing.Process(
            target=write_change, args=(lv.dnsmasq_leases,)
        )
        p.start()
        self.assertIsNone(validate_ipv46_address(wait_for_ip(lv=lv)))

    def test_run_script(self):
        """
        Complete integration test of run_script.

        Requirements:
          - svn needs to contain demo data. (provision svn_demo_data.yml role)
          - test user (vagrant) needs same ssh key as uwsgi user.
          - /data/containers needs to be writable
          - /data/containers/centos-6-x86_64 needs to exist.

        """
        # Suffers permission problems.
        libvirt_image = processing_factories.ProcessingJobImageFactory(libvirt_image='centos-6-x86_64')
        environment = processing_factories.ProcessingEnvironmentFactory(libvirt_image=libvirt_image, repo='/demo_dataset/')
        job = processing_factories.ProcessingJobFactory(environment=environment, script='plaice2nc.py')
        uuid = job.pk
        if not os.path.exists('/tmp/results'):
            os.makedirs('/tmp/results')

        self.assertTrue(
            os.access('/data/containers', os.W_OK),
            '/data/containers is not writeable. chmod 777 /data/containers.'
        )
        kwargs = {
            'namespace': uuid,
            'username': job.environment.author.username,
            'image': job.environment.libvirt_image.libvirt_image,
            'interpreter': job.environment.libvirt_image.interpreter,
            'script_name': job.script,
            'svn_url': job.environment.get_repo_url(),
            'open_earth_tools': job.environment.open_earth
        }
        self.instances_running.append('instance-{0}'.format(uuid))
        run_script(**kwargs)

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.destroy', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.isActive', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_cleanup(self):
        """
        Test if destroy is called when clean has run.
        """
        tmp_image_base_dir = '/tmp/containers'
        self.config_tmp_image_dir(self.image_base_dir, tmp_image_base_dir)
        network_name = "test_network"
        uuid = uuid1()
        container_settings = {
            'base_dir': tmp_image_base_dir,
            'base_image': 'base_image'
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid, image='base_image', network_name=network_name
            )
            lv = self.patch_lv_obj(lv)
            instance_path = os.path.join(
                container_settings['base_dir'],
                lv.get_instance_name()
            )
            instance_name = lv.get_instance_name()
            lv.create()
            cleanup(uuid=uuid, image=container_settings['base_image'])
            domain = lv.domain
            self.assertFalse(os.path.exists(instance_path))
            vir_connect_obj = libvirt.open('lxc:///')
            self.assertEqual(domain.isActive(), 0)

    def fill_dir_with_bogus_files(self, amount=4, ext='.nc'):
        if not os.path.exists(self.test_results_data_dir):
            os.makedirs(self.test_results_data_dir)
        flist = []
        for n in range(0, amount):
            fpath = os.path.join(
                self.test_results_data_dir, 'result-{0}{1}'.format(n, ext)
            )
            logger.info('Creating file "{0}"'.format(fpath))
            open(fpath, 'a').close()
            flist.append(fpath)

        return flist

    def test_find_files(self):
        """
        Tests if find files adds .nc files to job.job_results.
        """
        self.assertListEqual(
            self.fill_dir_with_bogus_files(),
            sorted(find_files(path=self.test_results_data_dir, extension='.nc'))
        )

    def test_add_file_to_job_result(self):
        """
        Test if adds .nc files to job.job_results.
        """
        files = self.fill_dir_with_bogus_files(amount=1)
        job = processing_factories.ProcessingJobFactory()
        processing_job = add_file_to_job_result(job=job, file_path=files[0])
        self.assertEqual(
            unicode(processing_job.file),
            os.path.basename(files[0])
        )

    def test_add_multiple_files(self):
        """
        Goes wrong in run_script...
        """
        if not os.path.exists('/tmp/smedia'):
            os.makedirs('/tmp/smedia')

        files = self.fill_dir_with_bogus_files(amount=4)
        job = processing_factories.ProcessingJobFactory()
        for f in files:
            add_file_to_job_result(job=job, file_path=f)

        file_names = map(os.path.basename, files)
        obj_names = [unicode(res.file) for res in job.processing_result.all()]
        self.assertListEqual(sorted(file_names), sorted(obj_names))

    def test_add_file_to_job_result_recursive(self):
        raise NotImplementedError


class TestCommitTask(LibVirtTestMixin):
    dest_data_dir = '/tmp/opendap_test_data'

    @classmethod
    def setUpClass(cls):
        cls.source_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.source_files_dir = os.path.join(os.path.dirname(__file__), 'files')
        if os.path.exists(TestCommitTask.dest_data_dir):
            shutil.rmtree(TestCommitTask.dest_data_dir)

    def tearDown(self):
        re_nc_files = re.compile(r"^.*\.nc$")
        if os.path.exists(TestCommitTask.dest_data_dir):
            for path in os.listdir(self.dest_data_dir):
                if re_nc_files.match(path):
                    logger.info('Removing demo file: {0} '.format(path))
                    os.remove(os.path.join(self.dest_data_dir, path))

    @staticmethod
    def create_observation_data():
        """
        Create data dict with values from factories.
        """
        c = script_exec_factories.CompartmentFactory()
        mm = script_exec_factories.MeasurementMethodFactory()
        o = script_exec_factories.OrganFactory()
        p = script_exec_factories.ParameterFactory()
        pp = script_exec_factories.PropertyFactory()
        q = script_exec_factories.QualityFactory()
        srd = script_exec_factories.SpatialReferenceDeviceFactory()
        sd = script_exec_factories.SampleDeviceFactory()
        sm = script_exec_factories.SampleMethodFactory()
        u = script_exec_factories.UnitFactory()

    @override_settings(OPENDAP_DATA_DIR=dest_data_dir)
    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_commit_task_commits_netcdf(self):
        """
        Test if netcdfs are pushed to opendap directories.
        """
        job = processing_factories.ProcessingJobFactory(script='plaice2nc.py')
        ncfile = 'jarkusKB117_3736.nc'
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            ncfile
        )
        print job.environment.repo
        add_file_to_job_result(job=job, file_path=source)
        commit(prev_task_result=True, username=job.environment.author.username, namespace=job.pk)
        repo_files = os.listdir(os.path.join(
            self.dest_data_dir,
            job.environment.repo
        ))
        # Only one file should be in the repository
        self.assertEqual(len(repo_files), 1)
        # Make sure the jarkus file is the one in the repository.
        # DjangoFiler makes file names lowercase.
        print repo_files
        self.assertTrue(ncfile.lower() in repo_files)

    # if call_commit_command is mocked: what are we testing then? Nothing?
    # @override_settings(OPENDAP_DATA_DIR=dest_data_dir)
    # @override_settings(CONTAINER={'base_dir': '/tmp'})
    # @mock.patch('openearth.apps.script_execution_manager.commit_worker.CommitCSV.call_commit_command', lambda self, published: None)
    # def test_commit_task_commits_csv(self):
    #     """
    #     Test if CSV file is committed to database.
    #
    #     Description:
    #         test_data_summing.csv contains 3 rows of data and 1 header. This
    #         test inserts 3 rows of data into the database.
    #     """
    #     # This is not working because the management command is called
    #     # externally. It produces data, but puts it in the real database. ANot
    #     # test.
    #     [self.create_observation_data() for i in range(3)]
    #     job = processing_factories.ProcessingJobFactory(script='plaice2nc.py')
    #     source = os.path.join(
    #         self.source_files_dir,
    #         'test_data_summing.csv'
    #     )
    #     add_file_to_job_result(job=job, file_path=source)
    #     commit(
    #         prev_task_result=True,
    #         username=job.environment.author.username,
    #         namespace=job.pk
    #     )
    #     # Check if 3 rows are added.
    #     self.assertEqual(Observation.objects.all().count(), 3)

    @override_settings(OPENDAP_DATA_DIR=dest_data_dir)
    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_commit_task_does_not_crash_on_zero_bytes_file(self):
        """
        When the comitter task receives a 0 byte file, ncatted crashes.

        Check if the try/except clause handles this correctly.
        """
        job = processing_factories.ProcessingJobFactory(script='plaice2nc.py')
        source = os.path.join(
            '/tmp',
            'empty.nc'
        )
        open(source, 'w').close()
        add_file_to_job_result(job=job, file_path=source)
        self.assertIsNone(commit(
            prev_task_result=True,
            username=job.environment.author.username,
            namespace=job.pk
        ))

        #os.listdir(self.dest_data_dir)

    # def test_logger_task(self):
    #     logger_task.apply_async()
    #     logger_task.apply_async()
    #     logger_task.apply_async()
    #     logger_task.apply_async()
    #     logger_task.apply_async()

    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_setup_logger_has_single_handler(self):
        """
        Test if logger has no double added handlers.
        """
        uuid_1 = uuid1()
        create_results_dir(uuid_1)
        dir_1 = '/tmp/results-{0}'.format(uuid_1)
        cl1 = setup_logger('fake_user', uuid_1, '{0}/run.log'.format(dir_1))
        uuid_2 = uuid1()
        create_results_dir(uuid_2)
        dir_2 = '/tmp/results-{0}'.format(uuid_2)
        cl2 = setup_logger('fake_user', uuid_2, '{0}/run.log'.format(dir_2))
        print cl1.name
        self.assertEqual(len(cl1.handlers), 2)
        self.assertEqual(len(cl2.handlers), 2)
        self.assertNotEqual(cl1.handlers[0], cl2.handlers[0])

    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_setup_logger_creates_once(self):
        """
        Test if setuplogger creates logger + handlers once per logger.

        setup_logger may be called twice from the same worker thread. In that
        case it calls logger.getChild(namespace) twice. If no logic is applied,
        the file and websocket handlers are added again.

        This test makes sure this does not happen.
        """
        uuid_1 = uuid1()
        create_results_dir(uuid_1)
        dir_1 = '/tmp/results-{0}'.format(uuid_1)
        cl1 = setup_logger('fake_user', uuid_1, '{0}/run.log'.format(dir_1))
        num_handlers_when_called_once = len(cl1.handlers)
        cl1 = setup_logger('fake_user', uuid_1, '{0}/run.log'.format(dir_1))
        num_handlers_when_called_twice = len(cl1.handlers)
        self.assertEqual(
            num_handlers_when_called_once,
            2
        )
        self.assertEqual(
            num_handlers_when_called_once,
            num_handlers_when_called_twice,
            'It looks like the handlers are added twice.'
        )


    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_create_results_dir(self):
        uuid = uuid1()
        self.assertEqual(
            create_results_dir(uuid),
            '/tmp/results-{0}'.format(uuid)
        )

    @override_settings(CONTAINER={'base_dir': '/tmp'})
    def test_create_results_dir_twice(self):
        """
        Creating the results dir twice should not be a problem
        """
        uuid = uuid1()
        self.assertEqual(
            create_results_dir(uuid),
            '/tmp/results-{0}'.format(uuid)
        )
        self.assertEqual(
            create_results_dir(uuid),
            '/tmp/results-{0}'.format(uuid)
        )
