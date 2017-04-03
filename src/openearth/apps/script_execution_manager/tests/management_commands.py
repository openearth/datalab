from __future__ import unicode_literals
from collections import OrderedDict
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.test import TestCase
import hashlib
from django.test.utils import override_settings
import pandas
import os

from pandas.tslib import Timestamp

from ..management.commands import csv_worker
from openearth.apps.processing.tests.factories import ProcessingJobFactory
from openearth.apps.script_execution_manager.models import LocationPoint, \
    Compartment, Observation
from . import factories
from openearth.apps.script_execution_manager.tests.factories import \
    ObservationFactory


class MockStdout(object):
    """
    Simple class to mock management command: self.stdout.write.

    This attr somehow does not exist when making the command object like this:
    c = Command().
    """
    @staticmethod
    def write(l):
        print l

@override_settings(
    USE_TZ=False,
    RAVEN_CONFIG={},
)
class TestCSVWorkerCommand(TestCase):
    initiated = False
    """
    TODO: write tests for:
    - what happens when data in dumptable doesnt validate
    - what happens when data in location table doesnt validate
    """
    test_data = os.path.join(
        os.path.dirname(__file__),
        'files',
        'test_data.csv'
    )
    test_data_nan = os.path.join(
        os.path.dirname(__file__),
        'files',
        'test_data_nan.csv'
    )
    test_data_broken = os.path.join(
        os.path.dirname(__file__),
        'files',
        'test_data_broken.csv'
    )
    csv_cols = [
        'compartment', 'parameter', 'orig_srid', 'origx', 'origy', 'value',
        'sampledevice', 'measurementmethod', 'samplemethod', 'date',
        'property', 'quality', 'unit'
    ]

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        csv_worker.Command.stdout = MockStdout
        csv_worker.Command.stderr = MockStdout

        if not TestCSVWorkerCommand.initiated:
            TestCSVWorkerCommand.create_models_from_app('openearth.apps.script_execution_manager.tests')
            TestCSVWorkerCommand.initiated = True

        super(TestCSVWorkerCommand, cls).setUpClass(*args, **kwargs)

    @classmethod
    def create_models_from_app(cls, app_name):
        """
        Manually create Models (used only for testing) from the specified string app name.
        Models are loaded from the module "<app_name>.models"
        """
        from django.db import connection, DatabaseError
        from django.db.models.loading import load_app

        app = load_app(app_name)
        from django.core.management import sql
        from django.core.management.color import no_style
        sql = sql.sql_create(app, no_style(), connection)
        cursor = connection.cursor()
        for statement in sql:
            try:
                cursor.execute(statement)
            except DatabaseError, excn:
                print(excn.message)

    @staticmethod
    def get_dictified_chunk_data():
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
            'sampledevice': sd.description,
            'measurementmethod': mm.description,
            'samplemethod': sm.description,
            'date': Timestamp('2013-01-08 00:00:00'),
            'property': pp.description,
            'quality': q.description,
            'unit': u.description,
        }

    def test_validate_column_names(self):
        """
        Test if validation is ok if all csv_cols are given
        """
        cmd = csv_worker.Command()
        self.assertTrue(cmd.validate_column_names(cols=self.csv_cols))

    def test_validate_column_names_extra_col(self):
        """
        Test if validation is ok if extra csv_cols are given
        """
        cmd = csv_worker.Command()
        csv_cols = self.csv_cols + ['extra_col']
        self.assertTrue(cmd.validate_column_names(cols=csv_cols))

    def test_validate_column_names_missing_raises_exception(self):
        """
        Test if validation fails if csv_cols are missing
        """
        cmd = csv_worker.Command()
        self.assertRaisesRegexp(
            ValidationError,
            r"These columns '.*' are required, but missing in the CSV file.",
            cmd.validate_column_names,
            cols=self.csv_cols[0:5]
        )

    def test_validate_uuid(self):
        """
        Tests if uuid validation accepts correct uuid.
        :return:
        """
        cmd = csv_worker.Command()
        self.assertTrue(
            cmd.validate_uuid('a17fdc18-7b0f-491d-9e13-b26668aa40b4')
        )

    def test_validate_uuid_false_uuid(self):
        """
        Tests if uuid validation accepts erroneous uuid.
        :return:
        """
        cmd = csv_worker.Command()
        self.assertFalse(
            cmd.validate_uuid('blaat')
        )

    def test_concatenate_observation_data(self):
        """
        Tests if correctly ordered string is returned
        """
        cmd = csv_worker.Command()
        dictified_chunk = self.get_dictified_chunk_data()
        dictified_chunk.update({
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        })
        # pprint(dictified_chunk)
        od = OrderedDict(sorted(dictified_chunk.items(), key=lambda k: k[0]))
        expected = ''.join(map(str, od.values()))
        res = cmd.concatenate_observation_data(
            compartment=dictified_chunk['compartment'],
            date=dictified_chunk['date'],
            orig_srid=dictified_chunk['orig_srid'],
            origx=dictified_chunk['origx'],
            origy=dictified_chunk['origy'],
            measurementmethod=dictified_chunk['measurementmethod'],
            parameter=dictified_chunk['parameter'],
            property=dictified_chunk['property'],
            quality=dictified_chunk['quality'],
            sampledevice=dictified_chunk['sampledevice'],
            samplemethod=dictified_chunk['samplemethod'],
            unit=dictified_chunk['unit'],
            value=dictified_chunk['value']
        )
        self.assertEqual(expected, res)

    def test_chunk_to_dict(self):
        """
        Test if chunk_to_dict returns a list of arrays which match csv header
        """
        chunksize = 4
        reader = pandas.read_csv(
            self.test_data,
            chunksize=chunksize,
            parse_dates=['date']
        )
        cmd = csv_worker.Command()
        chunk = reader.get_chunk(chunksize)
        d = cmd.chunk_to_dict(chunk)
        self.assertEqual(len(d), chunksize)
        self.assertTrue(set(chunk.keys()) == set(d[0].keys()))
        self.assertTrue(set(d[0].values()) == set(chunk.values[0]))

    def test_dicitified_chunk_to_db_published(self):
        """
        Tests if results are inserted in the 'live' db structure.

        Description:
            The test tries 3 items from dictified_chunks, from which 2 should
            create a new LocationPoint.
            Next test is to check if the observation is marked published.
        """
        observation_published = True
        pj = ProcessingJobFactory()
        dictified_chunk = self.get_dictified_chunk_data()
        cmd = csv_worker.Command()
        unique_values = [
            {'origx': 74235.579, 'origy': 453534.925, 'value': 1.261},
            {'origx': 74235.579, 'origy': 453534.925, 'value': 1.2570000000000001},
            {'origx': 32.579, 'origy': 453534.925, 'value': 1.2590000000000001},
        ]
        dictified_chunks = map(
            lambda x: dict(x.items()+dictified_chunk.items()),
            unique_values
        )
        cmd.chunk_to_db(
            dictified_chunks,
            published=observation_published,
            processing_job=pj
        )
        lps = LocationPoint.objects.all()
        o = Observation.objects.all()[0]
        self.assertListEqual([pj.uuid], o.processing_jobs)
        self.assertEqual(
            lps.count(),
            2 # Might not work; because of bulk_create? point exists should check locally too?
        )
        self.assertTrue(Observation.objects.last().published)

    def test_dicitified_chunk_to_db_reuse(self):
        """
        Test if observations existing in db are reused and linked to opju.
        :return:
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        # uuid_1 = 'a17fdc18-7b0f-491d-9e13-b26668aa40b4'
        # uuid_2 = 'b28ged29-7b0f-592e-0f26-b27778aa41c5'
        lp = factories.LocationPointFactory()
        pj_1 = ProcessingJobFactory()
        pj_2 = ProcessingJobFactory()
        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        cmd.chunk_to_db(
            [unique_value],
            published=True,
            processing_job=pj_1
        )
        cmd.chunk_to_db(
            [unique_value],
            published=True,
            processing_job=pj_2
        )
        self.assertEqual(1, Observation.objects.all().count())
        o = Observation.objects.all()[0]
        self.assertListEqual([pj_1.uuid, pj_2.uuid], o.processing_jobs)

    def test_dicitified_chunk_to_db_unpublished(self):
        """
        Tests if results from tmp table are inserted in the 'live' db structure.

        Description:
            The test tries 3 items from dictified_chunks, from which 2 should
            create a new LocationPoint.
            Next test is to check if the observation is marked unpublished.
        """
        observation_published = False
        pj_1 = ProcessingJobFactory()
        dictified_chunk = self.get_dictified_chunk_data()
        cmd = csv_worker.Command()
        unique_values = [
            {'origx': 74235.579, 'origy': 453534.92600000004, 'value': 1.261},
            {'origx': 74235.579001, 'origy': 453534.92600000004, 'value': 1.2570000000000001},
            {'origx': 74238.578, 'origy': 453534.925, 'value': 1.2590000000000001},
        ]
        dictified_chunks = map(
            lambda x: dict(x.items()+dictified_chunk.items()),
            unique_values
        )
        cmd.chunk_to_db(
            dictified_chunks,
            published=observation_published,
            processing_job=pj_1
        )
        o = Observation.objects.all()[0]
        self.assertListEqual([pj_1.uuid], o.processing_jobs)
        lps = LocationPoint.objects.all()
        self.assertEqual(
            lps.count(),
            2
        )
        self.assertFalse(Observation.objects.last().published)

    def test_observation_exists_returns_observation_object(self):
        """
        When an observation with already existing data is inserted, an
        Observation object should be returned.
        """
        dictified_chunk = self.get_dictified_chunk_data()
        dictified_chunk.update({
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        })
        cmd = csv_worker.Command()
        # insert data, then call observation_exists with this data again.
        o = factories.ObservationFactory()
        # o.concatenated_data contains a string. Try if concatenated data is
        # found again.
        rv = cmd.observation_exists(o.concatenated_data)
        self.assertIsInstance(rv, Observation)

    def test_observation_not_exists_returns_none(self):
        """
        When a new observation is added, None should be returned.
        """
        dictified_chunk = self.get_dictified_chunk_data()
        dictified_chunk.update({
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        })
        cmd = csv_worker.Command()
        # insert data, then call observation_exists. It should not be found.
        factories.ObservationFactory()
        rv = cmd.observation_exists('Non Existing Data')
        self.assertIsNone(rv)

    def test_point_exists_returns_false(self):
        """
        Test if point_exists() returns false if LocationPoint doesnt exist.
        """
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        point = Point(float(lp.origx)+1, float(lp.origy), srid=4326)
        self.assertFalse(cmd.point_exists(point))

    def test_point_exists_returns_lp(self):
        """
        Test if point_exists() returns LocationPoint does exist.
        """
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        point = Point(float(lp.origx), float(lp.origy), srid=4326)
        self.assertEqual(cmd.point_exists(point), lp)

    def test_approximate_point_exists_returns_lp(self):
        """
        Test if point_exists() LocationPoint approx has same location.
        """
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        # TODO: ask if +0.000005 is approx 1 meter
        point = Point(float(lp.origx)+0.000005, float(lp.origy), srid=4326)
        self.assertIsInstance(cmd.point_exists(point), LocationPoint)
        self.assertEqual(cmd.point_exists(point), lp)

    def test_approximate_point_not_exists_returns_false(self):
        """
        Test if point_exists() returns false if LocationPoint doesnt exist.
        """
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        point = Point(float(lp.origx)+1.05, float(lp.origy), srid=4326)
        self.assertFalse(cmd.point_exists(point))

    def test_create_observation_contains_required_data(self):
        """
        Tests if an observation is created, with required data.

        Description:
            Required data is: processing_job_uuid in array of Observation
            object, also the environment id and script should be in
            processing_environments. Published should be True.
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        pj = ProcessingJobFactory()
        lp = factories.LocationPointFactory()

        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        result_dict = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj
        )
        self.assertIsInstance(
            result_dict,
            dict
        )
        key = result_dict.keys()[0]
        obs = result_dict[key]['observation']
        self.assertIsInstance(obs, Observation)
        self.assertTrue(obs.published)
        self.assertListEqual([pj.uuid], obs.processing_jobs)
        self.assertListEqual(
            obs.processing_environments,
            [self.make_env_hash(pj)]
        )

    def test_create_observation_with_nan_data(self):
        """
        Tests if an observation is created, with a csv which contains NaN values

        Description:
            Required data is: processing_job_uuid in array of Observation
            object, also the environment id and script should be in
            processing_environments. Published should be True.
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        pj = ProcessingJobFactory()
        lp = factories.LocationPointFactory()

        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        nan_values = {
            'sampledevice': float('NaN'),
            'measurementmethod': float('NaN'),
            'samplemethod': float('NaN'),
        }
        unique_value.update(nan_values)
        result_dict = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj
        )
        self.assertIsInstance(
            result_dict,
            dict
        )
        key = result_dict.keys()[0]
        obs = result_dict[key]['observation']
        self.assertIsInstance(obs, Observation)
        self.assertTrue(obs.published)
        self.assertListEqual([pj.uuid], obs.processing_jobs)
        self.assertListEqual(
            obs.processing_environments,
            [self.make_env_hash(pj)]
        )

    def test_create_observation_unpublished(self):
        """
        Tests if an observation is created, with published=False
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        lp = factories.LocationPointFactory()
        pj = ProcessingJobFactory()
        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        result_dict = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=False,
            processing_job=pj
        )
        self.assertIsInstance(
            result_dict,
            dict
        )
        key = result_dict.keys()[0]
        obs = result_dict[key]['observation']
        self.assertIsInstance(
            obs,
            Observation
        )
        self.assertFalse(obs.published)

    def test_create_observation_fails_on_wrong_input(self):
        """
        Tests for data integrity.

        Description:
            Additionaly checks if the exception raised, produces a human
            readable error.
        """

        dc_data_common = self.get_dictified_chunk_data()
        lp = factories.LocationPointFactory()
        pj = ProcessingJobFactory()
        cmd = csv_worker.Command()
        # mimic parsed CSV data
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        dc_data_common['compartment'] = 'Non existing compartment'
        dc_data_common['parameter'] = 'Non existing parameter'
        dc_data_common['quality'] = 'Non existing quality'
        dc_data_common['sampledevice'] = 'Non existing sampledevice'
        dc_data_common['samplemethod'] = 'Non existing samplemethod'
        unique_value.update(dc_data_common)
        self.assertRaisesRegexp(
            ObjectDoesNotExist,
            'CSV file contains values which are not correct:\n'
            'Compartment "Non existing compartment" does not exist.\n'\
            'Parameter "Non existing parameter" does not exist.\n'\
            'Quality "Non existing quality" does not exist.\n'\
            'SampleDevice "Non existing sampledevice" does not exist.\n'\
            'SampleMethod "Non existing samplemethod" does not exist.',
            cmd.create_observation,
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj
        )

    def test_create_observation_reuse_existing_observation_in_db(self):
        """
        Tests if an observation is created, with published=True
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        lp = factories.LocationPointFactory()
        pj_1 = ProcessingJobFactory()
        pj_2 = ProcessingJobFactory()
        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        result_dict_1 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_1
        )
        key_1 = result_dict_1.keys()[0]
        obs_1 = result_dict_1[key_1]['observation']
        # Save observation to db, which would have been saved by chunk_to_db's
        # bulk_create.
        obs_1.save()

        # Create same observation again. Should return the same observation
        # as above.
        result_dict_2 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_2
        )
        key_2 = result_dict_2.keys()[0]
        obs_2 = result_dict_2[key_2]['observation']
        self.assertEqual(obs_1.pk, obs_2.pk)
        self.assertEqual(2, len(obs_2.processing_jobs))
        self.assertListEqual([pj_1.uuid, pj_2.uuid], obs_2.processing_jobs)

        self.assertEqual(len(obs_2.processing_environments), 2)
        self.assertEqual(
            obs_2.processing_environments[0],
            self.make_env_hash(pj_1)
        )
        self.assertEqual(
            obs_2.processing_environments[1],
            self.make_env_hash(pj_2)
        )

    def test_create_observation_reuse_existing_observation_same_dataset(self):
        """
        Test if duplicate data within one dataset is detected.
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        pj_1 = ProcessingJobFactory()
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        result_dict_1 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_1
        )
        key_1 = result_dict_1.keys()[0]
        obs_1 = result_dict_1[key_1]['observation']

        # Store results in internal registry
        # This is what makes it locally.
        cmd.observations.update(result_dict_1)

        # Create same observation again. Should return the same observation
        # as above.
        result_dict_2 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_1
        )
        key_2 = result_dict_2.keys()[0]
        obs_2 = result_dict_2[key_2]['observation']
        self.assertEqual(obs_1.pk, obs_2.pk)
        self.assertEqual(1, len(obs_2.processing_jobs))
        self.assertListEqual([pj_1.uuid], obs_2.processing_jobs)
        self.assertEqual(len(obs_2.processing_environments), 1)

    def test_create_observation_reuse_observation_from_db_and_local(self):
        """
        Test if duplicate data within dataset AND db is detected.

        Description:
            First store data in database; then try to add same data again with
            a different processingjob uuid. This mimics a new run of the commit
            script. Because it is the same data, the first observation from the
            db should be found. Another create should find the observation from
            the local registry again.
        """
        dictified_chunk_data_common = self.get_dictified_chunk_data()
        pj_1 = ProcessingJobFactory()
        pj_2 = ProcessingJobFactory()
        lp = factories.LocationPointFactory()
        cmd = csv_worker.Command()
        unique_value = {
            'origx': 74235.579,
            'origy': 453534.92600000004,
            'value': 1.261
        }
        unique_value.update(dictified_chunk_data_common)
        result_dict_1 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_1
        )
        key_1 = result_dict_1.keys()[0]
        obs_1 = result_dict_1[key_1]['observation']
        # Save to DB; different uuid indicates a different process has committed
        # this data.
        obs_1.save()

        # Next mimic a new process.
        cmd = csv_worker.Command()
        # Create same observation again. Should return the same observation
        # as above.
        result_dict_2 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_2
        )
        key_2 = result_dict_2.keys()[0]
        obs_2 = result_dict_2[key_2]['observation']

        # Store in process local registry
        cmd.observations.update(result_dict_2)

        # Create same observation again. This should find the existing instance.
        result_dict_3 = cmd.create_observation(
            location_point=lp,
            dictified_chunk=unique_value,
            published=True,
            processing_job=pj_2
        )
        key_3 = result_dict_3.keys()[0]
        obs_3 = result_dict_3[key_3]['observation']

        self.assertEqual(obs_1.pk, obs_2.pk)
        self.assertEqual(obs_2.pk, obs_3.pk)
        self.assertEqual(2, len(obs_3.processing_jobs))
        self.assertListEqual([pj_1.uuid, pj_2.uuid], obs_2.processing_jobs)
        self.assertEqual(len(obs_2.processing_environments), 2)

    def test_no_rows_inserted_on_import_fail(self):
        """
        Tests if transaction is aborted and no rows are inserted on failure.
        """
        from django.core.management import call_command
        # test_data_broken is 3 rows, make sure at least these are added.
        print [self.get_dictified_chunk_data() for i in range(3)]
        processing_job = ProcessingJobFactory()
        self.assertEqual(0, LocationPoint.objects.count())
        kwargs = {"csv_input": self.test_data_broken,
                  "processing_job": processing_job.uuid}
        args = ('csv_worker',)
        self.assertRaises(ObjectDoesNotExist, call_command, *args, **kwargs)
        self.assertEqual(0, LocationPoint.objects.count())

    @staticmethod
    def make_env_hash(pj):
        return hashlib.md5('{0}{1}'.format(
            pj.environment.pk,
            pj.script
        )).hexdigest()

    def test_remove_observation_reference_on_re_run(self):
        """
        Test if old observations related to the same environment are deleted.
        """
        pj_1 = ProcessingJobFactory()
        pj_2 = ProcessingJobFactory()
        pj_3 = ProcessingJobFactory()



        o1 = ObservationFactory(processing_environments=[
            self.make_env_hash(pj_1),
            self.make_env_hash(pj_2),
            self.make_env_hash(pj_3)
        ])
        o2 = ObservationFactory(processing_environments=[
            self.make_env_hash(pj_1)
        ])
        o3 = ObservationFactory(processing_environments=[
            self.make_env_hash(pj_2)
        ])
        env_hash = self.make_env_hash(pj_1)
        # Be sure the has is in the environments list
        self.assertIn(env_hash, o1.processing_environments)
        # Be sure there are 3 envs in the list
        self.assertEqual(len(o1.processing_environments), 3)
        self.assertIn(env_hash, o2.processing_environments)
        self.assertNotIn(env_hash, o3.processing_environments)
        cmd = csv_worker.Command()
        cmd.remove_or_deref_observations(processing_job=pj_1)
        observations_cleared_1 = Observation.objects.get(pk=o1.pk)
        self.assertRaises(ObjectDoesNotExist, Observation.objects.get, pk=o2.pk)
        observations_cleared_3 = Observation.objects.get(pk=o3.pk)
        self.assertListEqual(
            [self.make_env_hash(pj_2), self.make_env_hash(pj_3)],
            observations_cleared_1.processing_environments
        )
        self.assertListEqual(
            [self.make_env_hash(pj_2)],
            observations_cleared_3.processing_environments
        )

class TestLowerCaseCharfield(TestCase):

    def test_pre_save_with_string(self):
        testval = "This Should Be Stored Lowercase"
        c = Compartment.objects.create(
            code="TST",
            description=testval,
            number=1
        )
        self.assertEqual(
            c.description,
            testval.lower()
        )


    def test_pre_save_with_blank(self):
        testval = ''
        c = Compartment.objects.create(
            code="TST",
            description=testval,
            number=1
        )
        self.assertEqual(
            c.description,
            testval
        )



