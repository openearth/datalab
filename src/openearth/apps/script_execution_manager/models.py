from __future__ import unicode_literals
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gis_models
from django.db import models
from south.modelsinspector import add_introspection_rules
from djorm_pgarray.fields import TextArrayField


class LowerCaseCharField(models.CharField):
    """
    Character field which alters string to lower case.
    """

    def pre_save(self, model_instance, add):
        old_value = getattr(model_instance, self.attname)
        if old_value:
            setattr(model_instance, self.attname, old_value.lower())
        return getattr(model_instance, self.attname)

add_introspection_rules([], [
    "^openearth.apps.script_execution_manager.models.LowerCaseCharField"
])


class Compartment(models.Model):
    """
    Description of the compartment from which the sample has been taken
    """
    code = models.CharField(max_length=12) #character varying(12) NOT NULL,
    number = models.CharField(max_length=12) #character varying(12) NOT NULL,
    description = LowerCaseCharField(max_length=60, db_index=True) #character varying(60) NOT NULL,
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True) # Why?

    def __unicode__(self):
        return self.description


class Group(models.Model):
    """
    Full description of the group
    """
    description = models.TextField()

    def __unicode__(self):
        return self.description


class LocationPoint(gis_models.Model):
    """
    Stores location points. Observations relate to these points.

    Description:
        Points within 1 meter of each other are merged into one point by the
        csv commit script.
    """
    thegeometry = gis_models.GeometryField(spatial_index=True, srid=4326)#, geography=True)
    orig_srid = models.IntegerField()
    origx = models.FloatField()
    origy = models.FloatField()
    # TODO: deze wordt nergens gebruikt in pointworker. Kan weg?
    description = models.CharField(max_length=255, blank=True)
    published = models.BooleanField(default=False) # unused, so far.
    objects = gis_models.GeoManager()

    def __unicode__(self):
        return '{0}, {1} ({2})'.format(self.origx, self.origy, self.orig_srid)


class MeasurementMethod(models.Model):
    """
    Describes which measurement methods have been used
    """
    classification = models.TextField()
    description = LowerCaseCharField(db_index=True, max_length=255)
    link = models.TextField(
        blank=True,
        help_text='Optional link to full description of measurement type'
    )
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)

    def __unicode__(self):
        return self.description


class Observation(models.Model):
    """
    Observation table. Observations should be unique. ProcessingJobs which
    process observations are stored in the processing_jobs array field.
    """
    date = models.DateTimeField(db_index=True)  # timestamp without time zone
    value = models.FloatField()  # double precision NOT NULL,
    remark = models.CharField(max_length=255, blank=True)
    station = models.CharField(max_length=75, blank=True)  # unused?
    location = models.ForeignKey('LocationPoint', on_delete=models.DO_NOTHING)
    compartment = models.ForeignKey('Compartment', blank=True, null=True, on_delete=models.DO_NOTHING)
    organ = models.ForeignKey('Organ', blank=True, null=True)  # unused?
    property = models.ForeignKey('Property', blank=True, null=True, on_delete=models.DO_NOTHING)
    unit = models.ForeignKey('Unit', blank=True, null=True, on_delete=models.DO_NOTHING)
    quality = models.ForeignKey('Quality', blank=True, null=True, on_delete=models.DO_NOTHING)
    parameter = models.ForeignKey('Parameter', blank=True, null=True, on_delete=models.DO_NOTHING)
    sample_device = models.ForeignKey('SampleDevice', blank=True, null=True, on_delete=models.DO_NOTHING)
    sample_method = models.ForeignKey('SampleMethod', blank=True, null=True,  on_delete=models.DO_NOTHING)
    measurement_method = models.ForeignKey('MeasurementMethod', blank=True, null=True, on_delete=models.DO_NOTHING)
    published = models.BooleanField(default=False)  # used to be blstatus. TODO: Remove
    concatenated_data = models.TextField(db_index=True, unique=True)
    processing_jobs = TextArrayField()
    processing_environments = TextArrayField()

    def __unicode__(self):
        return '{0} - ({1}..{2})'.format(
            self.pk,
            self.concatenated_data[0:16],
            self.concatenated_data[-16:]
        )


class Parameter(models.Model):
    """
    Parameter table

    Description:
        This is the parameter database. The database consists of a serial key
        (parameter), a field with a general description (in case of species
        names, this is the scientific name), foreign key and a table name. The
        combination tablename and foreign key form a unique combination and will
        be used as a constraint.
    """
    description = LowerCaseCharField(
        max_length=255,
        db_index=True,
        help_text='Description derived from the reference_table (i.e. species, '
                  'chemical characteristic, sediment characteristic)'
    )
    reference_id = models.PositiveIntegerField(
        help_text="Refers to the id of the reference table selected in "
                  "reference table."
    )
    # reference_table = models.ForeignKey(
    #     'ReferenceTable',
    #     help_text='Reference table with detailed description of the parameter '
    #               'involved'
    # )
    content_type = models.ForeignKey(
        ContentType,
        help_text='Reference table to make relation to'
    )
    reference_table_parameter = GenericForeignKey('content_type', 'reference_id')

    def __unicode__(self):
        return self.description


# class ReferenceTable(models.Model):
#     """
#     Holds names for reference tables like the WoRMS database.
#
#     Description:
#         This model acts as an ENUM for Parameter.reference_table.
#     """
#     description = models.TextField()
#     url = models.URLField(help_text='URL of the database', blank=True)
#
#     def __unicode__(self):
#         return self.description[:30]


class ReferenceTableWormsParameter(models.Model):
    """
    Stores id of species from the WoRMS database [1]

    Description:
        The observation model has a property 'reference' which points to this
        (and possibly other) models with a generic foreign key.

        reference_id is a foreignkey and matches the numbers from the WoRMS
        register [1].

        This model has not a lot of properties. Other referencetables like
        sediment might have other properties in a table like this.

        1: http://www.marinespecies.org/
    """
    reference_id = models.PositiveIntegerField(
        help_text="Refers to an ID in the WoRMS register",
        unique=True,
        primary_key=True
    )
    # url = models.URLField(help_text='URL of the database', blank=True)

    def __unicode__(self):
        return self.description[:30]

    class Meta:
        verbose_name = 'Reference table WoRMS parameter'


class Property(models.Model):
    """
    Property table
    """
    description = LowerCaseCharField(db_index=True, max_length=255)
    reference = models.TextField(
        blank=True,
        help_text='Optional reference to documentation on the property'
    )
    code = models.CharField(blank=True, max_length=12)

    def __unicode__(self):
        return self.description

    class Meta:
        verbose_name_plural = 'properties'


class Organ(models.Model):
    """
    Organ table
    """
    code = models.CharField(max_length=12)
    description = LowerCaseCharField(max_length=60, db_index=True)
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)

    def __unicode__(self):
        return self.description


class Quality(models.Model):
    """
    """
    code = models.CharField(max_length=12)
    description = LowerCaseCharField(max_length=60, db_index=True)
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)

    def __unicode__(self):
        return self.description

    class Meta:
        verbose_name_plural = 'qualities'


class SampleDevice(models.Model):
    """
    Describes the available sample devices.
    """
    description = LowerCaseCharField(max_length=255, blank=True, db_index=True)
    link = models.TextField(
        help_text='Optional link to full description of the device'
    )
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)
    code = models.IntegerField()
    spatial_reference_device = models.ForeignKey('SpatialReferenceDevice', blank=True, null=True)

    def __unicode__(self):
        return self.description


class SampleMethod(models.Model):
    """
    Describes the available sample methods
    """
    classification = models.TextField(blank=True)
    description = LowerCaseCharField(db_index=True, max_length=255)
    link = models.TextField(
        blank=True,
        help_text='optional link to sample method description'
    )
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)
    reference = models.TextField(blank=True)
    code = models.CharField(max_length=12)

    def __unicode__(self):
        return self.description


class SpatialReferenceDevice(models.Model):
    """
    """
    code = models.IntegerField()
    description = LowerCaseCharField(
        blank=True,
        max_length=255,
        db_index=True,
        help_text='Optional link to online source for description'
    )

    def __unicode__(self):
        return self.description


class Unit(models.Model):
    """
    Describes the available unit types.
    """
    code = models.CharField(max_length=12)
    description = LowerCaseCharField(max_length=255, db_index=True)
    conversion_factor = models.CharField(max_length=12, blank=True)
    alias = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=255, blank=True)
    dimension = models.CharField(max_length=12, blank=True)
    group = models.ForeignKey('Group', on_delete=models.DO_NOTHING, blank=True, null=True)

    def __unicode__(self):
        return self.description
