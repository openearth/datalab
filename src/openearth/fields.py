from django.core.exceptions import ValidationError
from django.forms import CharField, PasswordInput
from passwords.validators import validate_length, common_sequences, dictionary_words, complexity
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

PASSWORD_IVALID_CHARCTERS = getattr(settings, "PASSWORD_IVALID_CHARCTERS", None)


class InvalidCharsValidator(object):
    message = _("Invalid Character(s) ({0})")
    code = "invalid_chars"

    def __init__(self, invalid_chars=None):
        self.invalid_chars = set(invalid_chars)

    def __call__(self, value):
        if self.invalid_chars is None:
            return
        if any((char in value) for char in self.invalid_chars):
            raise ValidationError(
                self.message.format(_("One or more characters are invalid")),
                code=self.code)

invalid_characters = InvalidCharsValidator(PASSWORD_IVALID_CHARCTERS)


class PasswordField(CharField):
    default_validators = [invalid_characters, validate_length, common_sequences, dictionary_words, complexity]

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key("widget"):
            kwargs["widget"] = PasswordInput(render_value=False)

        super(PasswordField, self).__init__(*args, **kwargs)
