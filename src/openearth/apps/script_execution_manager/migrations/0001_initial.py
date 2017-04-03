# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Compartment'
        db.create_table(u'script_execution_manager_compartment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=60, db_index=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Compartment'])

        # Adding model 'Group'
        db.create_table(u'script_execution_manager_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'script_execution_manager', ['Group'])

        # Adding model 'LocationPoint'
        db.create_table(u'script_execution_manager_locationpoint', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('thegeometry', self.gf('django.contrib.gis.db.models.fields.GeometryField')()),
            ('orig_srid', self.gf('django.db.models.fields.IntegerField')()),
            ('origx', self.gf('django.db.models.fields.FloatField')()),
            ('origy', self.gf('django.db.models.fields.FloatField')()),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'script_execution_manager', ['LocationPoint'])

        # Adding model 'MeasurementMethod'
        db.create_table(u'script_execution_manager_measurementmethod', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('classification', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=255, db_index=True)),
            ('link', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['MeasurementMethod'])

        # Adding model 'Observation'
        db.create_table(u'script_execution_manager_observation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
            ('remark', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('station', self.gf('django.db.models.fields.CharField')(max_length=75, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.LocationPoint'], on_delete=models.DO_NOTHING)),
            ('compartment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Compartment'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('organ', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Organ'], null=True, blank=True)),
            ('property', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Property'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Unit'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('quality', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Quality'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Parameter'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('sample_device', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.SampleDevice'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('sample_method', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.SampleMethod'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('measurement_method', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.MeasurementMethod'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('concatenated_data', self.gf('django.db.models.fields.TextField')(unique=True, db_index=True)),
            ('processing_jobs', self.gf('djorm_pgarray.fields.TextArrayField')(default=None, dbtype='text', null=True, blank=True)),
            ('processing_environments', self.gf('djorm_pgarray.fields.TextArrayField')(default=None, dbtype='text', null=True, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Observation'])

        # Adding model 'Parameter'
        db.create_table(u'script_execution_manager_parameter', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=255, db_index=True)),
            ('reference_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
        ))
        db.send_create_signal(u'script_execution_manager', ['Parameter'])

        # Adding model 'ReferenceTableWormsParameter'
        db.create_table(u'script_execution_manager_referencetablewormsparameter', (
            ('reference_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['ReferenceTableWormsParameter'])

        # Adding model 'Property'
        db.create_table(u'script_execution_manager_property', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=255, db_index=True)),
            ('reference', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Property'])

        # Adding model 'Organ'
        db.create_table(u'script_execution_manager_organ', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=60, db_index=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Organ'])

        # Adding model 'Quality'
        db.create_table(u'script_execution_manager_quality', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=60, db_index=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Quality'])

        # Adding model 'SampleDevice'
        db.create_table(u'script_execution_manager_sampledevice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(db_index=True, max_length=255, blank=True)),
            ('link', self.gf('django.db.models.fields.TextField')()),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('code', self.gf('django.db.models.fields.IntegerField')()),
            ('spatial_reference_device', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.SpatialReferenceDevice'], null=True, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['SampleDevice'])

        # Adding model 'SampleMethod'
        db.create_table(u'script_execution_manager_samplemethod', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('classification', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=255, db_index=True)),
            ('link', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('reference', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12)),
        ))
        db.send_create_signal(u'script_execution_manager', ['SampleMethod'])

        # Adding model 'SpatialReferenceDevice'
        db.create_table(u'script_execution_manager_spatialreferencedevice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.IntegerField')()),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(db_index=True, max_length=255, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['SpatialReferenceDevice'])

        # Adding model 'Unit'
        db.create_table(u'script_execution_manager_unit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('description', self.gf('openearth.apps.script_execution_manager.models.LowerCaseCharField')(max_length=255, db_index=True)),
            ('conversion_factor', self.gf('django.db.models.fields.CharField')(max_length=12, blank=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('link', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('dimension', self.gf('django.db.models.fields.CharField')(max_length=12, blank=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['script_execution_manager.Group'], null=True, on_delete=models.DO_NOTHING, blank=True)),
        ))
        db.send_create_signal(u'script_execution_manager', ['Unit'])


    def backwards(self, orm):
        # Deleting model 'Compartment'
        db.delete_table(u'script_execution_manager_compartment')

        # Deleting model 'Group'
        db.delete_table(u'script_execution_manager_group')

        # Deleting model 'LocationPoint'
        db.delete_table(u'script_execution_manager_locationpoint')

        # Deleting model 'MeasurementMethod'
        db.delete_table(u'script_execution_manager_measurementmethod')

        # Deleting model 'Observation'
        db.delete_table(u'script_execution_manager_observation')

        # Deleting model 'Parameter'
        db.delete_table(u'script_execution_manager_parameter')

        # Deleting model 'ReferenceTableWormsParameter'
        db.delete_table(u'script_execution_manager_referencetablewormsparameter')

        # Deleting model 'Property'
        db.delete_table(u'script_execution_manager_property')

        # Deleting model 'Organ'
        db.delete_table(u'script_execution_manager_organ')

        # Deleting model 'Quality'
        db.delete_table(u'script_execution_manager_quality')

        # Deleting model 'SampleDevice'
        db.delete_table(u'script_execution_manager_sampledevice')

        # Deleting model 'SampleMethod'
        db.delete_table(u'script_execution_manager_samplemethod')

        # Deleting model 'SpatialReferenceDevice'
        db.delete_table(u'script_execution_manager_spatialreferencedevice')

        # Deleting model 'Unit'
        db.delete_table(u'script_execution_manager_unit')


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