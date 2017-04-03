from __future__ import unicode_literals
from decimal import Decimal
from django.contrib.gis.geos import Point
import factory
from factory.django import DjangoModelFactory
import uuid
import datetime
from ..models import LocationPoint, Compartment, MeasurementMethod, Organ, Parameter, Property, Quality, \
    SpatialReferenceDevice, SampleDevice, SampleMethod, Unit, Observation
from openearth.apps.script_execution_manager.tests.models import DummyModel


class LocationPointFactory(DjangoModelFactory):
    FACTORY_FOR = LocationPoint
    origx = factory.Sequence(lambda n: Decimal('74235.579') + n)
    origy = factory.Sequence(lambda n: Decimal('453534.92600000004') + n)
    orig_srid = factory.Sequence(lambda n: 28992)
    description = factory.Sequence('Description #{0}'.format)
    # This might not work, because it is not really the same as origx and origy
    thegeometry = factory.Sequence(lambda n: Point(74235.579+n, 453534.92600000004+n))


class CompartmentFactory(DjangoModelFactory):
    FACTORY_FOR = Compartment
    code = factory.Sequence("C{0}".format)
    description = factory.Sequence("Compartment description {0}".format)
    number = factory.Sequence("{0}".format)


class MeasurementMethodFactory(DjangoModelFactory):
    FACTORY_FOR = MeasurementMethod
    link = ''
    description = factory.Sequence("Measurement method description {0}".format)
    classification = factory.Sequence("MM{0}".format)


class OrganFactory(DjangoModelFactory):
    FACTORY_FOR = Organ
    code = factory.Sequence("O{0}".format)
    description = factory.Sequence("Organ description {0}".format)


class DummyModelFactory(DjangoModelFactory):
    FACTORY_FOR = DummyModel
    reference_id = factory.sequence(lambda n: 109603)


class ParameterFactory(DjangoModelFactory):
    FACTORY_FOR = Parameter
    reference_table_parameter = factory.SubFactory(DummyModelFactory)
    description = factory.Sequence('Parameter_level_{0}'.format)


class PropertyFactory(DjangoModelFactory):
    FACTORY_FOR = Property
    description = factory.Sequence('Property {0}'.format)
    code = factory.Sequence('code{0}'.format)
    reference = u'http://domeintabellen-idsw.rws.nl/DomeinWaardenEdit.aspx zoek op hoedanigheid'


class QualityFactory(DjangoModelFactory):
    FACTORY_FOR = Quality
    code = factory.Sequence('{0}'.format)
    description = factory.Sequence('Quality value {0}'.format)


# class ReferenceTableFactory(DjangoModelFactory):
#     FACTORY_FOR = models.ReferenceTable
#     description = factory.Sequence('description {0}'.format)
#     url = factory.Sequence('http://www.site-{0}.com'.format)


class SpatialReferenceDeviceFactory(DjangoModelFactory):
    FACTORY_FOR = SpatialReferenceDevice
    description = u'Akoestische afstandsmeter'
    code = 201


class SampleDeviceFactory(DjangoModelFactory):
    FACTORY_FOR = SampleDevice
    code = factory.Sequence('{0}'.format)
    link = u'http://domeintabellen-idsw.rws.nl/DomeinWaardenEdit.aspx zoek op bemonsteringsapparaat'
    spatial_reference_device_id = ''
    description = factory.Sequence('Sample device {0}'.format)


class SampleMethodFactory(DjangoModelFactory):
    FACTORY_FOR = SampleMethod
    reference = factory.Sequence('Sample method ref {0}'.format)
    code = factory.Sequence('I19458.0{0}'.format)
    classification = ''
    # description = factory.Sequence('NEN-EN-ISO 19458:2007-{0}'.format)
    description = factory.Sequence('Nen-en-iso 19458:2007-{0}'.format)
    link = u'http://domeintabellen-idsw.rws.nl/DomeinWaardenEdit.aspx zoek op bemonsteringsmethode'


class UnitFactory(DjangoModelFactory):
    FACTORY_FOR = Unit
    alias = factory.Sequence('Unit alias {0}'.format)
    link = ''
    dimension = ''
    conversion_factor = ''
    code = '%'
    description = factory.Sequence('Unit description {0}'.format)


class ObservationFactory(DjangoModelFactory):
    FACTORY_FOR = Observation
    date = datetime.datetime.now()
    value = 1.111
    remark = factory.Sequence('Remark {0}'.format)
    station = factory.Sequence('Station {0}'.format)
    location = factory.SubFactory(LocationPointFactory)
    compartment = factory.SubFactory(CompartmentFactory)
    organ = factory.SubFactory(OrganFactory)
    property = factory.SubFactory(PropertyFactory)
    unit = factory.SubFactory(UnitFactory)
    quality = factory.SubFactory(QualityFactory)
    parameter = factory.SubFactory(ParameterFactory)
    sample_device = factory.SubFactory(SampleDeviceFactory)
    sample_method = factory.SubFactory(SampleMethodFactory)
    measurement_method = factory.SubFactory(MeasurementMethodFactory)
    published = True
    concatenated_data = factory.Sequence('concatenated data here {0}'.format)
    # FK not possible  probably, due to multi db(?)
    processing_jobs = factory.Sequence(function=lambda x: [uuid.uuid1()])
    processing_environments = factory.Sequence(function=lambda x: [[0+x, 'script.py']])
