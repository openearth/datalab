from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from openearth.apps.processing.fields import InterpreterField
from openearth.apps.processing.tests import factories
from string import Formatter


class InterpreterFieldTest(TestCase):
    """
    Tests if Field validates missing template keys correctly.

    Description:
        value = 'asdasd {key1} {key2}' with required keys: key1, key2 is fine
        value = 'asdasd {key1}' with required keys: key1, key2 raises an error.
        value = 'asdasd {key1} {key2} {key3}' with required keys: key1, key2
        raises an error.
    """
    def test_field_validation_error_on_missing_keys(self):
        # pjif = factories.ProcessingJobImageFactory()
        field = InterpreterField(required_keys=['key1', 'key2', 'key3'])
        value = '/opt/bin/interpreter {key1} --interpreter_options {key2}'
        self.assertRaisesRegexp(
            ValidationError,
            u'Value is missing keys: {key3}',
            field.validate,
            value
        )

    def test_field_validation_succeeds_on_correct_keys(self):
        # pjif = factories.ProcessingJobImageFactory()
        field = InterpreterField(required_keys=['key1'])
        value = '/opt/bin/interpreter {key1} --interpreter_options'
        self.assertIsNone(field.validate(value))

    def test_field_validation_error_on_too_many_keys(self):
        # pjif = factories.ProcessingJobImageFactory()
        field = InterpreterField(required_keys=['key1'])
        value = '/opt/bin/interpreter {key1} --interpreter_options {key2}'
        self.assertRaisesRegexp(
            ValidationError,
            u'Value has unused keys: {key2}',
            field.validate,
            value
        )


        # print val.check_unused_args()

