# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Documentation.description'
        db.alter_column(u'documentation_documentation', 'description', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'Documentation.description'
        db.alter_column(u'documentation_documentation', 'description', self.gf('django.db.models.fields.CharField')(max_length=255))

    models = {
        u'documentation.documentation': {
            'Meta': {'object_name': 'Documentation'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['documentation']