from __future__ import unicode_literals

from django.contrib.auth.models import User

from django.contrib.auth.tests.utils import skipIfCustomUser

from django.forms.fields import Field, CharField
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_text
from ..forms import UserCreationForm
import string
import random

# The minimal password requirements are:
# - Password Length = 8
# - Number of uppercase characters = 1
# - Number of lowercase characters = 1
# - Number of digist = 1
# - Number of punctuation characters = 0
# - Number of non ascii characters (except @) = 0
# - Number of words (substrings separated by whitespace) = 0

@skipIfCustomUser
@override_settings(
    USE_TZ=False,
    PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
)
class UserCreationFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_password_min_length_requirement(self):
        data = {
            'username': 'testclient1',
            'password1': 'Test123',
            'password2': 'Test123',
        }

        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['password_min_length'])])

    def test_password_max_length_requirement(self):
        pw = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in xrange(121))
        data = {
            'username': 'testclient2',
            'password1': pw,
            'password2': pw,
        }

        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['password_max_length'])])

    def test_password_uppercase_requirement(self):
        data = {
            'username': 'testclient3',
            'password1': 'testing123',
            'password2': 'testing123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['password_num_uppercase'])])

    def test_password_lowercase_requirement(self):
        data = {
            'username': 'testclient4',
            'password1': 'TESTING123',
            'password2': 'TESTING123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['password_num_lowercase'])])

    def test_password_digits_requirement(self):
        data = {
            'username': 'testclient5',
            'password1': 'Testingpassword',
            'password2': 'Testingpassword',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['password_num_digits'])])

    def test_password_invalid_character_requirement(self):
        data = {
            'username': 'testclient6',
            'password1': 'Testing@password123',
            'password2': 'Testing@password123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password1"].errors,
                         [force_text(form.error_messages['invalid_characters'])])