from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm as OriginalUserCreationForm
from django.contrib.auth.forms import AdminPasswordChangeForm as OriginalAdminPasswordChangeForm
from django.utils.translation import ugettext_lazy as _
import ldap
from .fields import PasswordField
from django.conf import settings
from django.utils.safestring import mark_safe
from .libs.auth import create_user, change_password
from openearth.libs.auth import PASSWORD_HELP_TEXT, add_user_to_groups


class UserCreationForm(OriginalUserCreationForm):

    error_messages = {
        'duplicate_username':
            _("A user with that username already exists."),
        'password_mismatch':
            _("The two password fields didn't match."),
        'password_min_length':
            _("Invalid Length (Must be {0} characters or more)".format(settings.PASSWORD_MIN_LENGTH)),
        'password_max_length':
            _("Invalid Length (Must be {0} characters or less)".format(settings.PASSWORD_MAX_LENGTH)),
        'password_num_uppercase':
            _("Must be more complex (Must contain {0} or more uppercase characters)".format(
                settings.PASSWORD_COMPLEXITY["UPPER"])
              ),
        'password_num_lowercase':
            _("Must be more complex (Must contain {0} or more lowercase characters)".format(
                settings.PASSWORD_COMPLEXITY["LOWER"])
              ),
        'password_num_digits':
            _("Must be more complex (Must contain {0} or more digits)".format(
                settings.PASSWORD_COMPLEXITY["DIGITS"])
              ),
        'invalid_characters': _("Invalid Character(s) (One or more characters are invalid)"),
    }

    username = forms.RegexField(label=_("Username"), max_length=30,
                                regex=r'^[\w.@+-]+$',
                                help_text=_("Required. 30 characters or fewer. Letters, digits and "
                                            "@/./+/-/_ only."),
                                error_messages={
                                    'invalid': _("This value may contain only letters, numbers and "
                                                 "@/./+/-/_ characters.")})

    password1 = PasswordField(label=_("Password"),
                              help_text=_(mark_safe(PASSWORD_HELP_TEXT)),
                              widget=forms.PasswordInput)
    password2 = PasswordField(label=_("Password confirmation"),
                              help_text=_("Enter the same password as above, for verification."))

    first_name = forms.CharField(label=_("First name"), max_length=30)
    last_name = forms.CharField(label=_("Last name"), max_length=30)
    email = forms.EmailField(label=_('Email'), max_length=75)

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        try:
            #  change ldap password
            create_user(user, self.cleaned_data['password1'])
            # Add user to the default groups 'restrictedDatasetUser' and 'svnUser' set by DEFAULT_USER_GROUPS
            # in settings or pass a tuple with groupnames (CN of group in ldap)
            add_user_to_groups(user)
            # a user only needs an password in django to be able to login in the admin
            user.set_unusable_password()
        except:
            raise
        if commit:
            user.save()
        return user


class PasswordPolicyAuthenticationForm(AuthenticationForm):
    username = forms.CharField(max_length=254)
    password = PasswordField(label=_("Password"))

class AdminPasswordChangeForm(forms.Form):
    """
    A form used to change the password of a user in the admin interface.
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }

    password1 = PasswordField(label=_("Password"),
                              widget=forms.PasswordInput)
    password2 = PasswordField(label=_("Password (again)"),
                              widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(AdminPasswordChangeForm, self).__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def save(self, commit=True):
        """
        Saves the new password.
        """
        try:
            # Change password in LDAP
            change_password(self.user.username, self.cleaned_data["password1"])
        except ldap.LDAPError, e:
            if not self.user.is_staff and not self.user.is_superuser:
                # Only raise an error if not superuser or staff because they can
                # exist in django only
                raise

        if self.user.is_staff or self.user.is_superuser:
            # Only set the password in django if user is staff or superuser
            self.user.set_password(self.cleaned_data["password1"])
        else:
            # for good measure
            self.user.set_unusable_password()

        if commit:
            self.user.save()
        return self.user

    def _get_changed_data(self):
        data = super(AdminPasswordChangeForm, self).changed_data
        for name in self.fields.keys():
            if name not in data:
                return []
        return ['password']
    changed_data = property(_get_changed_data)