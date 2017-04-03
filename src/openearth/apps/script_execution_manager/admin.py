from __future__ import unicode_literals
from django.contrib import admin
from .models import Compartment, Group, LocationPoint, MeasurementMethod, \
    Observation, Organ, Parameter, Property, Quality, SampleDevice, \
    SampleMethod, SpatialReferenceDevice


class ObservationAdmin(admin.ModelAdmin):
    list_display = ('value', 'date', 'published', 'station', 'location',
                    'compartment', 'organ', 'property', 'unit', 'quality',
                    'parameter', 'sample_device', 'sample_method',
                    'measurement_method')
    list_filter = ('date', 'published')
    search_fields = ('value', 'compartment__description', 'organ__description',
                    'property__description', 'unit__description',
                    'quality__description', 'parameter__description',
                    'sample_device__description', 'sample_method__description',
                    'measurement_method__description')
    raw_id_fields = ('parameter',)


class GroupAdmin(admin.ModelAdmin):
    list_display = ('description',)
    search_fields = ('description',)


class CompartmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'code', 'number')
    search_fields = ('description', 'code', 'number')


class MeasurementMethodAdmin(admin.ModelAdmin):
    list_display = ('description', 'classification', 'group')
    list_filter = ('group',)
    search_fields = ('description', 'classification')


class OrganAdmin(admin.ModelAdmin):
    list_display = ('description', 'code', 'group')
    list_filter = ('group',)
    search_fields = ('description', 'code')


class ParameterAdmin(admin.ModelAdmin):
    #list_display = ('description', 'reference_table')
    #list_filter = ('reference_table',)
    search_fields = ('description',)


class PropertyAdmin(admin.ModelAdmin):
    list_display = ('description', 'code', 'reference')
    search_fields = ('description', 'code')


class QualityAdmin(admin.ModelAdmin):
    list_display = ('description', 'code', 'group')
    list_filter = ('group',)
    search_fields = ('description', 'code')


class SampleDeviceAdmin(admin.ModelAdmin):
    list_display = ('description', 'group', 'spatial_reference_device', 'code', 'link')
    list_filter = ('spatial_reference_device',)
    search_fields = ('description',)


class SampleMethodAdmin(admin.ModelAdmin):
    list_display = ('description', 'group', 'code')
    list_filter = ('group',)
    search_fields = ('description', 'code')


class SpatialReferenceDeviceAdmin(admin.ModelAdmin):
    list_display = ('description', 'code')
    search_fields = ('description',)


admin.site.register(Compartment, CompartmentAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(LocationPoint)
admin.site.register(MeasurementMethod, MeasurementMethodAdmin)
admin.site.register(Observation, ObservationAdmin)
admin.site.register(Organ, OrganAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Property, PropertyAdmin)
admin.site.register(Quality, QualityAdmin)
admin.site.register(SampleDevice, SampleDeviceAdmin)
admin.site.register(SampleMethod, SampleMethodAdmin)
admin.site.register(SpatialReferenceDevice, SpatialReferenceDeviceAdmin)