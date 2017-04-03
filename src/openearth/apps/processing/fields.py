from __future__ import unicode_literals
from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from string import Formatter

from django.utils.translation import ugettext_lazy as _

class InterpreterField(forms.Field):
    """
    Checks if value contains {script_name} (or other keys)

    Description:
        The value should contain template keys like {script_name}. Another
        module can use the value of this field, and format it. Example
        value = '/opt/python/bin/python {script_name} --option --another'

        Another module uses:
        value.format(script_name='bla.py')
        Which results in:
        '/opt/python/bin/python bla.py --option --another'
    """
    widget = forms.TextInput(attrs={'size':'120'})

    def __init__(self, required_keys=set(), *args, **kwargs):
        super(InterpreterField, self).__init__(*args, **kwargs)
        self.required_keys = set(required_keys)

    def validate(self, value):
        """
        Check if {keys} are in the string.
        """
        def wrap_keys(key):
            return '{{{0}}}'.format(key)

        # Use the parent's handling of required fields, etc.
        super(InterpreterField, self).validate(value)
        f = Formatter()
        keys_found = set(filter(None, [it[1] for it in f.parse(value)]))
        missing_keys = self.required_keys.difference(keys_found)
        if missing_keys:
            prep_keys = map(wrap_keys, missing_keys)
            raise ValidationError(_('Value is missing keys: {0}.'.format(', '.join(prep_keys))))

        too_many_keys = keys_found.difference(self.required_keys)
        if too_many_keys:
            prep_keys = map(wrap_keys, too_many_keys)
            raise ValidationError(_('Value has unused keys: {0}.'.format(', '.join(prep_keys))))
