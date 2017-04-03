from __future__ import unicode_literals
from django.db import connection
from django.test import TestCase
from factory import DjangoModelFactory
import inspect
import os
import re
from netCDF4 import Dataset
import logging

from pandas.tslib import Timestamp

from ..models import Observation
from ..commit_worker import CommitError, CommitNetCDF, CommitCSV, \
    CommitKML  #, CommitKML
from . import factories
from openearth.apps.processing.tests.factories import ProcessingJobFactory


logger = logging.getLogger(__name__)


class TestCommitCSV(TestCase):
    """
    Tests committing of individual CSV files to database.

    Description:
        First tests publishing methods, next part is testing unpublish.
        Finally test commit method.
    """

    test_data = os.path.join(
        os.path.dirname(__file__),
        'files',
        'test_data_summing.csv'
    )

    @classmethod
    def setUpClass(cls):
        # truncate observation related data, so all sequences start at one
        # again.
        tables = [
            'script_execution_manager_compartment',
            'script_execution_manager_group',
            'script_execution_manager_locationpoint',
            'script_execution_manager_measurementmethod',
            'script_execution_manager_observation',
            'script_execution_manager_organ',
            'script_execution_manager_parameter',
            'script_execution_manager_property',
            'script_execution_manager_quality',
            'script_execution_manager_sampledevice',
            'script_execution_manager_samplemethod',
            'script_execution_manager_spatialreferencedevice',
            'script_execution_manager_unit'
        ]
        for table_name in tables:
            print 'Flushing table "{0}"'.format(table_name)
            cursor = connection.cursor()
            cursor.execute('TRUNCATE TABLE "{0}" CASCADE'.format(table_name))

        print 'Resetting factory sequence'

        # Gets all attribuets from factories module,
        # then filters out all class types, excluding DjangoModelFactory.
        # If class is a subtype of DjangoModelFactory: set sequence to 0.
        # Setting the sequence to 0, makes testing with csv files possible.
        # A CSV file contains hardcoded sequence number (eg: description 2).
        # When a test is run with previous calls to factory objects, sequence id
        # 2 might be taken and deleted from the database. Next item will be 3,
        # items 1, 2 are missing from the database. The CSV (which contains
        # description 2) will not validate.
        for i in dir(factories):
            attr = getattr(factories, i)
            if inspect.isclass(attr) and not attr is DjangoModelFactory:
                if issubclass(attr, DjangoModelFactory):
                    attr.reset_sequence()

    @staticmethod
    def get_dictified_chunk_data(id):
        """
        Create data dict with values from factories.
        """
        c = factories.CompartmentFactory()
        mm = factories.MeasurementMethodFactory()
        o = factories.OrganFactory()
        p = factories.ParameterFactory()
        pp = factories.PropertyFactory()
        q = factories.QualityFactory()
        srd = factories.SpatialReferenceDeviceFactory()
        sd = factories.SampleDeviceFactory()
        sm = factories.SampleMethodFactory()
        u = factories.UnitFactory()

        return {  # add origx, origy and value later.
            'compartment': c.description,
            'parameter': p.description,
            'orig_srid': 28992,
            'sample_device': sd.description,
            'measurement_method': mm.description,
            'sample_method': sm.description,
            'date': Timestamp('2013-01-08 00:00:00'),
            'property': pp.description,
            'quality': q.description,
            'unit': u.description
        }
    # Mocking call_commit_command does not make sense if you'e testing it.
    # And mocking is required, because it calls the management command with
    # subprocess. Because this command is called with subprocess, the management
    # command executes not in testing mode. So it uses production database.
    # Not possible to test against.
    #
    # def test_call_commit_command(self):
    #     data = [self.get_dictified_chunk_data(i) for i in range(3)]
    #     print data
    #
    #     pj = ProcessingJobFactory()
    #     ccsv = CommitCSV(source=self.test_data, processing_job=pj)
    #
    #     # dit werkt niet, omdat het command dat uitgevoerd wordt dus niet de
    #     # test-database gebruikt. Mock: subprocess.Popen(cmd, stderr=subprocess.PIPE)?
    #     ccsv.call_commit_command()
    #     #for row in data:
    #     #    self.assertIsInstance(
    #     #        Observation.objects.get(compartment__description=row['compartment']),
    #     #        Observation
    #     #    )
    #
    # def test_mark_published_marks_data_published(self):
    #     pass
    #
    # def test_mark_unpublished_marks_data_unpublished(self):
    #     pass
    #
    # def test_broken_data_gives_proper_error_message(self):
    #     pass



class TestCommitNetCDF(TestCase):
    """
    Tests committing of individual netcdf files.

    Description:
        First tests publishing methods, next part is testing unpublish.
        Finally test commit method.
    """
    @classmethod
    def setUpClass(cls):
        cls.source_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.dest_data_dir = '/tmp'

    def setUp(self):
        self.pj = ProcessingJobFactory()

    def tearDown(self):
        re_nc_files = re.compile(r"^.*nc$")
        for path in os.listdir(self.dest_data_dir):
            if re_nc_files.match(path):
                logger.info('Removing demo file: {0} '.format(path))
                os.remove(os.path.join(self.dest_data_dir, path))

    #
    # First test mark published
    #

    def test_mark_published_adds_attribute_processing_level(self):
        """
        Test if adding processing_level attributes to nc file works

        We also test if the processing job is equal to the job's uuid
        """

        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'nc_cf_grid_write_x_y_orthogonal_tutorial.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_published())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        rootgrp.getncattr('processing_job')


        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'final'
        )

        # we also test if the processing job is equal to the job's uuid
        self.assertEqual(
            rootgrp.getncattr('processing_job'),
            self.pj.pk
        )
        rootgrp.close()

        # Test if source is untouched
        rootgrp = Dataset(filename=source, mode='r')
        self.assertNotIn('processing_level', rootgrp.ncattrs())
        rootgrp.close()

    def test_mark_published_changes_attribute_processing_level(self):
        """
        Test if file from source dir is marked published in dest dir.

        Also checks if source is still untouched.
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_published())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'final'
        )

        rootgrp.close()

        # Test if source is untouched
        rootgrp = Dataset(filename=source, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'preliminary'
        )
        rootgrp.close()

    def test_mark_published_file_exists_overwrites(self):
        dummy_file = os.path.join(self.dest_data_dir, 'dummy.nc')
        open(dummy_file, 'a').close()
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736.nc'
        )
        dest = dummy_file
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_published())
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'final'
        )
        rootgrp.close()

    def test_mark_published_raises_error_on_wrong_return_code(self):
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'i_do_not_exist.nc'
        )
        dest = os.path.join(
            self.dest_data_dir,
            'me_neither.nc'
        )
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertRaisesRegexp(
            CommitError,
            r'ncatted:\ ERROR\ file.*',
            cncdf.mark_published
        )

    #
    # Second test mark published
    #
    def test_mark_unpublished_adds_attribute_processing_level(self):
        """
        Test if adding processing_level attributes to nc file works
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'nc_cf_grid_write_x_y_orthogonal_tutorial.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_unpublished())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'preliminary'
        )
        rootgrp.close()

        # Test if source is untouched
        rootgrp = Dataset(filename=source, mode='r')
        self.assertNotIn('processing_level', rootgrp.ncattrs())
        rootgrp.close()

    def test_mark_unpublished_changes_attribute_processing_level(self):
        """
        Test if file from source dir is marked published in dest dir.

        Also checks if source is still untouched.
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736_final.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736_final.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_unpublished())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'preliminary'
        )
        rootgrp.close()

        # Test if source is untouched
        rootgrp = Dataset(filename=source, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'final'
        )
        rootgrp.close()

    def test_mark_unpublished_file_exists_overwrites(self):
        dummy_file = os.path.join(self.dest_data_dir, 'dummy.nc')
        open(dummy_file, 'a').close()
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736_final.nc'
        )
        dest = dummy_file
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(cncdf.mark_unpublished())
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'preliminary'
        )
        rootgrp.close()

    def test_mark_unpublished_raises_error_on_wrong_return_code(self):
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'i_do_not_exist.nc'
        )
        dest = os.path.join(
            self.dest_data_dir,
            'me_neither.nc'
        )
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertRaisesRegexp(
            CommitError,
            r'ncatted:\ ERROR\ file.*',
            cncdf.mark_unpublished
        )

    def test_commit_published(self):
        """
        Tests if file is published when commit is called.
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736_final.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj, published=True)
        self.assertIsNone(cncdf.commit())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'final'
        )

        # we also test if the processing job is equal to the job's uuid
        self.assertEqual(
            rootgrp.getncattr('processing_job'),
            self.pj.pk
        )
        rootgrp.close()

    def test_commit_unpublished(self):
        """
        Tests if file is published when commit is called.
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'jarkusKB117_3736_final.nc'
        )
        dest = os.path.join(self.dest_data_dir, 'jarkusKB117_3736_final.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj, published=False)
        self.assertIsNone(cncdf.commit())

        # Test if dest is changed correctly
        rootgrp = Dataset(filename=dest, mode='r')
        rootgrp.getncattr('processing_level')
        self.assertEqual(
            rootgrp.getncattr('processing_level'),
            'preliminary'
        )
        rootgrp.close()
    #
    # def test_task_does_not_run_in_parallel(self):
    #     """
    #     Test if a task can only have one instance at a time.
    #     """

    def test_try_empty_file_raises_error(self):
        """
        Tests if empty file raises exception
        """
        source = '/tmp/empty.nc'
        open(source, 'a').close()
        dest = os.path.join(self.dest_data_dir, 'empty.nc')
        cncdf = CommitNetCDF(source=source, dest=dest, processing_job=self.pj)
        self.assertRaises(CommitError, cncdf.mark_published)


class TestCommitKML(TestCase):
    """
    Tests committing of individual kml files.

    Description:
        First tests publishing methods, next part is testing unpublish.
        Finally test commit method.
    """
    @classmethod
    def setUpClass(cls):
        cls.source_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.dest_data_dir = '/tmp'

    def setUp(self):
        self.pj = ProcessingJobFactory()

    def tearDown(self):
        re_kml_files = re.compile(r"^.*kml$")
        for path in os.listdir(self.dest_data_dir):
            if re_kml_files.match(path):
                logger.info('Removing demo file: {0} '.format(path))
                os.remove(os.path.join(self.dest_data_dir, path))

    #
    # First test mark published
    #
    def test_mark_published_copies_file(self):
        """
        Test if adding processing_level attributes to nc file works
        """
        source = os.path.join(
            self.source_data_dir,
            'commit_results',
            'KML_Samples.kml'
        )
        dest = os.path.join(self.dest_data_dir, 'KML_Samples.kml')
        ckml = CommitKML(source=source, dest=dest, processing_job=self.pj)
        self.assertIsNone(ckml.mark_published())
        # Test if file exists in kml dir.
