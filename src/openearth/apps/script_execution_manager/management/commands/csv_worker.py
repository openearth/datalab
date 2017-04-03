from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import reset_queries, transaction, connection
import hashlib
from optparse import make_option
import os
import pandas
import re
import math
from openearth.apps.processing.models import ProcessingJob
from openearth.apps.script_execution_manager.models import LocationPoint, \
    Compartment, SampleMethod, Parameter, SampleDevice, MeasurementMethod, \
    Property, Quality, Unit, Observation
import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This command validates CSV data and inserts it into the database.

    Description:
        It also marks the data as published or unpublished.
        This is the base command for CommitCSV, which in turn is called after
        a processing job has succesfully finished and when it has produced CSV
        files.

        While this command also could have been a library, this management
        command is made for easier testing. Also the CommitNetCDF class calls
        an external program.
    """
    option_list = BaseCommand.option_list + (
        make_option(
            '--csv-input',
            dest='csv_input',
            help='Path to CSV formatted file.'
        ),
        make_option(
            '--published',
            action='store_true',
            dest='published',
            help='Mark the data as published',
            default=False
        ),
        make_option(
            '--processing-job',
            dest='processing_job',
            help='ProcessingJob UUID',
            default=''
        ),
    )
    required_csv_columns = {
        'compartment', 'parameter', 'orig_srid', 'origx', 'origy', 'value',
        'sampledevice', 'measurementmethod', 'samplemethod', 'date', 'property',
        'quality', 'unit'
    }

    # observation object registry with a dicht which contains Observation
    # objects and their state (created, or existing).
    observations = {}

    def validate_uuid(self, uuid):
        """
        Rude check if uuid is in correct uuid1 format.

        Description:
            Format like: a17fdc18-7b0f-491d-9e13-b26668aa40b4
        Returns:
            True if correct, False if incorrect.
        """
        match = re.match(
            r'([a-z0-9]+)-([a-z0-9]+)-([a-z0-9]+)-([a-z0-9]+)-([a-z0-9]+)',
            uuid
        )
        if match:
            return True

        return False

    def validate_column_names(self, cols):
        """
        Checks if the CSV file contains all required columns.

        Description:
            Checking is fairly dumb, only the columns names are checked. Content
            is not. Content of the colums will be checked when trying to insert
            it into the database.
        Arguments:
            cols: a list with the column names from the CSV header.
        """
        self.stdout.write('Verifying CSV header')
        csv_cols = set(cols)
        if self.required_csv_columns <= csv_cols:
            return True
        else:
            missing_cols = set(self.required_csv_columns).difference(csv_cols)
            raise ValidationError(
                "These columns '{0}' are required, but missing in the CSV "
                "file.".format(
                    ', '.join(missing_cols)
                )
            )

    def concatenate_observation_data(
        self, compartment, date, measurementmethod, orig_srid, origx, origy,
        parameter, property, quality, sampledevice, samplemethod, unit, value,
    ):
        """
        Concatenate observation data into one string.

        Arguments:
            All important fields of the generated CSV file.
        Description:
            Used by "observation_exists" to determine if this kind of data is
            already inserted into the database. This method is fairly dumb, it
            does no type-checking whatsoever.
            Ordering of data field names is alphabetically

        Returns:
            String with concatenated data
        """
        # Convert to string before joining
        data = map(str, [
            compartment, date, measurementmethod, orig_srid, origx, origy,
            parameter, property, quality, sampledevice, samplemethod, unit,
            value
        ])
        return ''.join(data)

    @staticmethod
    def chunk_to_dict(chunk):
        """
        Parses chunk and puts it in a dict, which is used to insert data in DB.

        Arguments:
            chunk: a panda's data frame object
        Returns:
            dict: in the form of:
                [{'field_name': value}, {'field_name': value}]
        """
        csv_cols = chunk.keys()
        return [dict(zip(csv_cols, v)) for v in chunk.values]

    @staticmethod
    def make_env_hash(pj):
        return hashlib.md5('{0}{1}'.format(
            pj.environment.pk,
            pj.script
        )).hexdigest()

    def remove_or_deref_observations(self, processing_job):
        """
        Removes Observations or removes related Environments.

        Arguments:
            observations is a Queryset object with Observations.
        """
        cursor = connection.cursor()
        env_hash = self.make_env_hash(processing_job)
        # Update observations which have the same environment setup.
        # Removes these items from the array.
        self.stdout.write('Dereference environment {0} in observations.'.format(env_hash))
        cursor.execute("""
            UPDATE script_execution_manager_observation
            SET processing_environments=array_remove(processing_environments, '{env_hash}')
            WHERE processing_environments @> ARRAY['{env_hash}']
        """.format(env_hash=env_hash))

        # Remove observations without related environments
        self.stdout.write('Removing observations without related processing_environments')
        Observation.objects.filter(processing_environments=[]).delete()

    def observation_exists_locally(self, concatenated_observation_data):
        """
        Check if concatenated_observation_data is in self.observations
        Returns:
            Non-saved Observation object.
        """
        local_observation = self.observations.get(
            concatenated_observation_data,
            None
        )
        if local_observation:
            return local_observation['observation']

    def observation_exists(self, concatenated_observation_data):
        """
        Checks if an observation with the same data already exists.

        Description:
            Checks first in self.observations_concatenated_data. If not in list,
            find in database.

        Returns:
            Observation Object if a match is found, None if not.
        """
        local_observation = self.observation_exists_locally(
            concatenated_observation_data
        )
        if local_observation:
            return local_observation

        try:
            return Observation.objects.get(
                concatenated_data=concatenated_observation_data
            )
        except ObjectDoesNotExist:
            return None

    def processing_job_exists(self, uuid):
        return ProcessingJob.objects.filter(uuid=uuid).exists()

    def point_exists(self, point):
        """
        Returns False if point does not exist, else return locationpoint id

        Description:
            Translates the original query to a django raw orm query.
            The dimension of 1 is lat/long. According to this [1] post on Stack-
            Overflow, 0.0001 is approx 1.11m.

        Arguments:
            point is a Point to check within a range.

        Returns:
            False or LocationPoint object
        """
        qs = LocationPoint.objects.raw("""
            SELECT * FROM script_execution_manager_locationpoint
            WHERE st_dwithin(
                thegeometry,
                st_transform(
                  st_setsrid(
                    st_point({point.x}, {point.y}), {point.srid}),
                    4326
                  ),
                  -- This should be approximately one meter.
                  -- See: http://stackoverflow.com/a/8477438/198050
                  -- 0.00001
                  -- Gerrit Hendriksen (gerrit.hendriksen@deltares.nl) says
                  -- 8*10e-6 is approximately one meter.
                  8.181818181818181e-06
            )
            """.format(point=point)
        )

        res = sum(1 for result in qs)
        return qs[0] if res else False

    def create_observation(
        self, location_point, dictified_chunk, published, processing_job
    ):
        """
        Create observation related to existing or new LP.

        Description:
            Before trying to bind an observation to a location_point, check if
            all values are correct. It tries all values in a CSV row.
            All errors will be displayed in a human readable error message.
            An ObjectDoesNotExist exception will be raised.

        Returns a dict with the Observation object. The dict also describes if
            the observation is new (created=True) or found in either the
            database or local registry (created=False)

        """
        errors = []

        def get_relations(model, field):
            """
            Gets relation or adds error message to errors list. Errors should be
            descriptive to user. (Standard DoesNotExist errors are not.)

            If a value is NaN, None is returned.
            """
            field_iexact = '{0}__exact'.format(field)
            value = dictified_chunk[model.__name__.lower()]
            if type(value) == float and math.isnan(value):
                return None

            try:
                return model.objects.get(**{
                    field_iexact: value.lower()
                })
            except ObjectDoesNotExist:
                errors.append('{0} "{1}" does not exist.'.format(
                    model.__name__,
                    value
                ))

        compartment = get_relations(Compartment, 'description')
        measurementmethod = get_relations(MeasurementMethod, 'description')
        parameter = get_relations(Parameter, 'description')
        property_ = get_relations(Property, 'description')
        quality = get_relations(Quality, 'description')
        sampledevice = get_relations(SampleDevice, 'description')
        samplemethod = get_relations(SampleMethod, 'description')
        unit = get_relations(Unit, 'description')
        if errors:
            errors = ['CSV file contains values which are not correct:'] \
                + errors
            raise ObjectDoesNotExist('\n'.join(errors))

        concatenated_data = self.concatenate_observation_data(
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
        existing_observation = self.observation_exists(concatenated_data)
        env_info = self.make_env_hash(processing_job)
        if existing_observation:
            # Add processing job to observation
            if processing_job.uuid not in existing_observation.processing_jobs:
                existing_observation.processing_jobs.append(processing_job.uuid)

            # Add environment info to observation
            if not existing_observation.processing_environments:
                existing_observation.processing_environments = [env_info]
            elif env_info not in existing_observation.processing_environments:
                existing_observation.processing_environments.append(env_info)

            return {
                concatenated_data: {
                    'observation': existing_observation,
                    'created': False
                }
            }
        else:
            observation = Observation(
                location=location_point,
                date=dictified_chunk['date'],
                compartment=compartment,
                measurement_method=measurementmethod,
                parameter=parameter,
                property=property_,
                quality=quality,
                sample_device=sampledevice,
                sample_method=samplemethod,
                unit=unit,
                value=dictified_chunk['value'],
                published=published,
                concatenated_data=concatenated_data,
                processing_jobs=[processing_job.uuid],
                processing_environments=[env_info]
            )
            return {
                concatenated_data: {
                    'observation': observation,
                    'created': True
                }
            }

    def chunk_to_db(self, dictified_chunks, published, processing_job):
        """
        Adds LocationPoint if it does not exists. Relates observation to point.

        Argument:
            dict from self.chunk_to_dict.
        """
        self.observations = {}
        new_location_points = []
        existing_location_points = []
        for dc in dictified_chunks:
            point = Point(dc['origx'], dc['origy'], srid=dc['orig_srid'])
            lp = self.point_exists(point)

            if not lp:
                lp = LocationPoint.objects.create(
                    origx=dc['origx'],
                    origy=dc['origy'],
                    orig_srid=dc['orig_srid'],
                    thegeometry=point
                )
                new_location_points.append(str(lp.id))
            else:
                existing_location_points.append(str(lp.id))

            create_result = self.create_observation(
                location_point=lp,
                dictified_chunk=dc,
                published=published,
                processing_job=processing_job
            )
            self.observations.update(create_result)

        self.stdout.write(
            'Writing {0} new LocationPoint objects to database, with IDs: '
            '{1}'.format(
                len(new_location_points),
                ', '.join(new_location_points)
            )
        )
        self.stdout.write(
            'Re-using {0} LocationPoint objects, with IDs: {1}'.format(
                len(existing_location_points),
                ', '.join(existing_location_points)
            )
        )
        new_observations = filter(
            lambda o: o['created'] is True,
            self.observations.values()
        )
        reused_observations = filter(
            lambda o: o['created'] is False,
            self.observations.values()
        )
        self.stdout.write(
            'Writing {0} Observation objects to database.'.format(
                len(new_observations)
            )
        )
        self.stdout.write(
            'Re-using {0} Observation objects, with IDs: {1}'.format(
                len(reused_observations),
                ', '.join([str(o['observation'].pk) for o in reused_observations])
            )
        )
        self.save_observations(self.observations)

    def save_observations(self, observations):
        """
        Saves all observations from the observation 'registry'.

        Description:
            Because the registry is a dict, get all Observation objects out of
            it. Only save observations. Related objects like
            ObservationProcessingJobUsage will be saved by method:
            save_observation_usage.

        """
        Observation.objects.bulk_create(
            [v['observation'] for v in observations.itervalues() if v['created']]
        )

        for v in observations.itervalues():
            if not v['created']:
                v['observation'].save()

    def handle(self, *args, **options):
        if not options['csv_input']:
            self.stderr.write(
                '--csv-input should contain the path to a CSV'
                ' formatted file'
            )

        if not os.path.isfile(options['csv_input']):
            self.stderr.write('This is not a file "{0}"'.format(
                options['csv_input']
            ))
        if not options['processing_job']:
            raise Exception('A processingjob uuid is required.')

        if options['processing_job']:
            if not self.validate_uuid(options['processing_job']):
                raise ValidationError('UUID is not in the correct format')
            if not self.processing_job_exists(options['processing_job']):
                raise Exception(
                    'ProcessingJob with UUID "{0}" does not exist.'.format(
                        options['processing_job']
                    )
                )

        processing_job = ProcessingJob.objects.get(uuid=options['processing_job'])
        # Remove old observations from same environment + script.
        self.remove_or_deref_observations(processing_job)
        logger.info("Importing {0}".format(options['csv_input']))
        reader = pandas.read_csv(
            options['csv_input'],
            chunksize=100,
            parse_dates=['date']
        )
        chunkno = 0
        with transaction.atomic():
            for chunk in reader:
                if not chunkno:
                    self.validate_column_names(chunk.dtypes.index)

                self.stdout.write('Chunk {0}'.format(chunkno))
                dictified_chunks = self.chunk_to_dict(chunk)
                self.chunk_to_db(
                    dictified_chunks,
                    options['published'],
                    # options['processing_job']
                    processing_job
                )
                chunkno += 1
                # Reset query log, which is recorded in debug mode.
                # This causes a massive memory leak:
                # 125k lines csv > 1000MB memory
                reset_queries()
