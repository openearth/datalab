from __future__ import print_function
from django.contrib.contenttypes.models import ContentType

from django.db.models import FieldDoesNotExist
from importlib import import_module
import json
import os
import re
from south.v2 import SchemaMigration
from django.db import connection
import sys
from django.db.models.fields.related import ForeignKey
from openearth.apps.script_execution_manager.models import \
    ReferenceTableWormsParameter


class Migration(SchemaMigration):
    """
    Imports data from json files in ./data/ dir. Files are parsed
    alphabetically. Prefixing with 01, 02 forces import order, which is required
    when foreignkeys point to other tables.

    This structure of importing data is used because there are no fixtures
    available. Data was (will?) delivered in another json format and needed to
    be converted to the current DB layout.

    field_maps Is used to map old field names to new field names. Values of None
    in the map, mean this field is not existing, should get the default value
    or an SQL NULL value is allowed.
    """
    # Map works like this:
    # old field name : new field name OR None if field does not exist in new
    # schema. If the field in the new schema is a foreign key, the related model
    # is automatically created. The only parameter it automatically gets is
    # description.
    field_maps = {
        'Compartment': {
            'compartmentcode': 'code',
            'compartmentdescription': 'description',
            'compartmentnumber': 'number',
            'idgroup': None,  # Does not exist in new schema.
            'idcompartment': None
        },
        'MeasurementMethod': {
            'measurementmethodtype': 'classification',
            'measurementmethoddescription': 'description',
            'measurementmethodlink': 'link',
            'idgroup': None,
            'measurement_method': None
        },
        'Organ': {
            'idorgan': None,
            'organcode': 'code',
            'organdescription': 'description',
            'idgroup': None
        },
        'Parameter': {
            'idparameter': None,
            'parameterdescription': 'description',
            'foreignkey': 'reference_id',  # a number
            # will be a foreign_key to content_type, which makes the Reference
            # table available. See generic foreignkey django docs.
            'referencetable': 'content_type'

        },
        'Property': {
            'idproperty': None,
            'propertydescription': 'description',
            'propertyreference': 'reference',
            'propertycode': 'code',
        },
        'Quality': {
            'idquality': None,
            'qualitycode': 'code',
            'qualitydescription': 'description',
            'idgroup': None
        },
        'SpatialReferenceDevice': {
            'idsrdevice': 'id',
            'srdevicecode': 'code',
            'srdevicedescription': 'description',
            'srdevicelink': None
        },
        'SampleDevice': {
            'idsampledevice': None,
            'sampledevicedescription': 'description',
            'sampledevicelink': 'link',
            'idgroup': None,
            'sampledevicecode': 'code',
            'idspatialreferencedevice': 'spatial_reference_device_id'
        },
        'SampleMethod': {
            'idsamplemethod': None,
            'samplemethodtype': 'classification',
            'samplemethoddescription': 'description',
            'samplemethodlink': 'link',
            'idgroup': None,
            'samplemethodreference': 'reference',
            'samplemethodcode': 'code'
        },
        'Unit': {
            'idunit': None,
            'unitcode': 'code',
            'unitdescription': 'description',
            'unitconversionfactor': 'conversion_factor',
            'unitalias': 'alias',
            'unitlink': 'link',
            'unitdimension': 'dimension',
            'idgroup': None,
            'groep': None,
        }

    }
    table_prefix = 'script_execution_manager'
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data')

    def get_model_from_table_name(self, orm, table_name):
        point_name = table_name.replace('{0}_'.format(self.table_prefix), '', 1)
        model_point_name = '{table_pfx}.{point_name}'.format(
            table_pfx=self.table_prefix,
            point_name='.'.join(point_name.split('_'))
        )
        print(model_point_name)
        return orm.models[model_point_name]

    def is_foreign_key_field(self, model, field_map, field):
        opts = model._meta
        model_field = None
        try:
            model_field = opts.get_field(field_map[field])
        except FieldDoesNotExist:
            pass

        return all([model_field, isinstance(model_field, ForeignKey)])

    def is_content_type_foreign_key_field(self, model, field_map, field):
        # Blargh
        opts = model._meta
        model_field = None
        related_model = None

        try:
            model_field = opts.get_field(field_map[field])
        except FieldDoesNotExist:
            pass

        if isinstance(model_field, ForeignKey):
            related_model = model_field.rel.to
            # unbound print(related_model.save())

        return all([
            model_field,
            related_model,
            isinstance(model_field, ForeignKey),
            # related_model == ContentType
            str(related_model) == "<class 'django.contrib.contenttypes.models.ContentType'>" # FUGLY
        ])

    def insert_data(self, orm, table_name, model, json_data):
        # Somehow something still goes wrong.
        # Probably the generated 04-parameter.json still contains duplicates.
        print('Using model "{0}"'.format(model))
        field_map = self.field_maps[model.__name__]
        for row in json_data:
            # Maps old key names to new key names. Skips mapped keys which are
            # None. Replaces None values with ''
            print('.', end='')
            # print(json_data)
            kwargs = {}
            for field in row:
                if field_map.get(field):
                    if self.is_content_type_foreign_key_field(model, field_map, field):
                        obj, created = orm.ReferenceTableWormsParameter.objects.get_or_create(
                            reference_id=row['foreignkey'],
                        )
                        ct_model = orm['contenttypes.ContentType']
                        try:
                            ct_obj = ct_model.objects.get(
                                app_label='script_execution_manager',
                                model='{0}'.format('ReferenceTableWormsParameter'.lower())
                            )
                            kwargs = {'description': row[field], 'content_type': ct_obj, 'reference_id': obj.pk }
                        except ContentType.DoesNotExist:
                            print('ContentType {0} does not exits for field {1}'.format(
                                'ReferenceTableWormsParameter'.lower(),
                                field
                                )
                            )
                            kwargs[field_map[field]] = ''

                    elif self.is_foreign_key_field(model, field_map, field):
                        # Create foreign keys automatically.
                        # Only works for FK's which only require a description
                        # to be set.
                        obj, created = orm.ReferenceTable.objects.get_or_create(
                            description=row[field]
                        )
                        kwargs[field_map[field]] = obj
                        # print('{0} {1} for field {2}'.format(
                        #     'created' if created else 'found',
                        #     obj,
                        #     field_map[field]
                        # ))
                    elif row[field]:
                        kwargs[field_map[field]] = row[field]
                    else:
                        kwargs[field_map[field]] = ''
            model.objects.create(**kwargs)
        print('done.')

    def forwards(self, orm):
        # print orm.models_source
        if 'test' in sys.argv:
            print(
                'Skipping inserting initial data, because it makes testing '
                'slow.'
            )
            return

        # Finally we may insert data!
        re_fname = re.compile(r'\d{2}\-(.*)\.json$')
        for filename in os.listdir(self.data_dir):
            print('Reading {0}'.format(filename))
            m_fname = re_fname.match(filename)
            table_name = '{0}_{1}'.format(
                self.table_prefix,
                m_fname.group(1)
            )
            with open(os.path.join(self.data_dir, filename), 'r') as fp:
                print('Inserting data into table "{0}"'.format(table_name))
                self.insert_data(
                    orm=orm,
                    table_name=table_name,
                    model=self.get_model_from_table_name(orm, table_name),
                    json_data=json.load(fp=fp)
                )

    def backwards(self, orm):
        # print orm.models_source
        re_fname = re.compile(r'\d{2}\-(.*)\.json')

        for filename in os.listdir(self.data_dir):
            print('Reading {0}'.format(filename))
            m_fname = re_fname.match(filename)
            table_name = '{0}_{1}'.format(
                self.table_prefix,
                m_fname.group(1)
            )
            print('Flushing table "{0}"'.format(table_name))
            cursor = connection.cursor()
            cursor.execute(
                'TRUNCATE TABLE "{0}" CASCADE'.format(table_name)
            )

    models = {
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'script_execution_manager.compartment': {
            'Meta': {'object_name': 'Compartment'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '60', 'db_index': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        u'script_execution_manager.group': {
            'Meta': {'object_name': 'Group'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'script_execution_manager.locationpoint': {
            'Meta': {'object_name': 'LocationPoint'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orig_srid': ('django.db.models.fields.IntegerField', [], {}),
            'origx': ('django.db.models.fields.FloatField', [], {}),
            'origy': ('django.db.models.fields.FloatField', [], {}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'thegeometry': ('django.contrib.gis.db.models.fields.GeometryField', [], {})
        },
        u'script_execution_manager.measurementmethod': {
            'Meta': {'object_name': 'MeasurementMethod'},
            'classification': ('django.db.models.fields.TextField', [], {}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '255', 'db_index': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'script_execution_manager.observation': {
            'Meta': {'object_name': 'Observation'},
            'compartment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Compartment']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'concatenated_data': ('django.db.models.fields.TextField', [], {'unique': 'True', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.LocationPoint']", 'on_delete': 'models.DO_NOTHING'}),
            'measurement_method': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.MeasurementMethod']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'organ': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Organ']", 'null': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Parameter']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'processing_environments': ('djorm_pgarray.fields.TextArrayField', [], {'default': 'None', 'dbtype': "'text'", 'null': 'True', 'blank': 'True'}),
            'processing_jobs': ('djorm_pgarray.fields.TextArrayField', [], {'default': 'None', 'dbtype': "'text'", 'null': 'True', 'blank': 'True'}),
            'property': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Property']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'quality': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Quality']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'remark': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sample_device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.SampleDevice']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'sample_method': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.SampleMethod']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'station': ('django.db.models.fields.CharField', [], {'max_length': '75', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Unit']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        u'script_execution_manager.organ': {
            'Meta': {'object_name': 'Organ'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '60', 'db_index': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'script_execution_manager.parameter': {
            'Meta': {'object_name': 'Parameter'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reference_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'script_execution_manager.property': {
            'Meta': {'object_name': 'Property'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reference': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'script_execution_manager.quality': {
            'Meta': {'object_name': 'Quality'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '60', 'db_index': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'script_execution_manager.referencetablewormsparameter': {
            'Meta': {'object_name': 'ReferenceTableWormsParameter'},
            'reference_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'primary_key': 'True'})
        },
        u'script_execution_manager.sampledevice': {
            'Meta': {'object_name': 'SampleDevice'},
            'code': ('django.db.models.fields.IntegerField', [], {}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.TextField', [], {}),
            'spatial_reference_device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.SpatialReferenceDevice']", 'null': 'True', 'blank': 'True'})
        },
        u'script_execution_manager.samplemethod': {
            'Meta': {'object_name': 'SampleMethod'},
            'classification': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '255', 'db_index': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'reference': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'script_execution_manager.spatialreferencedevice': {
            'Meta': {'object_name': 'SpatialReferenceDevice'},
            'code': ('django.db.models.fields.IntegerField', [], {}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'script_execution_manager.unit': {
            'Meta': {'object_name': 'Unit'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'conversion_factor': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'description': ('openearth.apps.script_execution_manager.models.LowerCaseCharField', [], {'max_length': '255', 'db_index': 'True'}),
            'dimension': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['script_execution_manager.Group']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        }
    }

    complete_apps = ['script_execution_manager']