from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
import os
import hashlib
import ldap
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.forms import SetPasswordForm
from django import forms
from django.conf import settings
from django.template import loader
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.contrib.sites.models import get_current_site
from django.utils.encoding import force_bytes
from openearth.fields import PasswordField

import logging
logger = logging.getLogger(__name__)


PASSWORD_COMPLEXITY = getattr(settings, 'PASSWORD_COMPLEXITY', {
    "UPPER": 1,        # Uppercase
    "LOWER": 1,        # Lowercase
    "DIGITS": 1,       # Digits
    "PUNCTUATION": 0,  # Punctuation (string.punctuation)
    "NON ASCII": 0,    # Non Ascii (ord() >= 128)
    "WORDS": 0         # Words (substrings seperates by a whitespace)
})

PASSWORD_HELP_TEXT = \
    "The minimal password requirements are:<br/>" \
    " - Password Length = {pw_length}<br/>"\
    " - Number of uppercase characters = {upper}<br/>"\
    " - Number of lowercase characters = {lower}<br/>"\
    " - Number of digist = {digits}<br/>"\
    " - Number of punctuation characters = {punctuation}<br/>"\
    " - Number of non ascii characters (except @) = {non_ascii}<br/>"\
    " - Number of words (substrings separated by whitespace) = {words}<br/>".format(
        pw_length=settings.PASSWORD_MIN_LENGTH,
        upper=PASSWORD_COMPLEXITY["UPPER"],
        lower=PASSWORD_COMPLEXITY["LOWER"],
        digits=PASSWORD_COMPLEXITY["DIGITS"],
        punctuation=PASSWORD_COMPLEXITY["PUNCTUATION"],
        non_ascii=PASSWORD_COMPLEXITY["NON ASCII"],
        words=PASSWORD_COMPLEXITY["WORDS"],
    )

DEFAULT_USER_GROUPS = getattr(settings, 'DEFAULT_USER_GROUPS', (
    'restrictedDatasetUser',
    'svnUser',
))

AUTH_LDAP_OU = getattr(settings, 'AUTH_LDAP_OU', 'users')
AUTH_LDAP_GROUPS_OU = getattr(settings, 'AUTH_LDAP_GROUPS_OU', 'groups')
LDAP_DC_FIRST = getattr(settings, 'LDAP_DC_FIRST', 'dc_first')
LDAP_DC_SECOND = getattr(settings, 'LDAP_DC_SECOND', 'dc_second')
AUTH_LDAP_SERVER_URI = getattr(settings, 'AUTH_LDAP_SERVER_URI', "ldap://localhost:389")
AUTH_LDAP_BIND_DN = getattr(settings, 'AUTH_LDAP_BIND_DN', "cn=admin,dc={0},dc={1}".format(LDAP_DC_FIRST, LDAP_DC_SECOND))
LDAP_ADMIN_PASSWD = getattr(settings, 'LDAP_ADMIN_PASSWD', None)


def _ldap_connection():
    logger.debug("Setup connection")
    con = ldap.initialize(AUTH_LDAP_SERVER_URI)
    con.set_option(ldap.OPT_REFERRALS, False)
    con.set_option(ldap.OPT_DEBUG_LEVEL, 255)
    con.set_option(ldap.VERSION, ldap.VERSION3)
    con.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    return con


def _get_next_uid():
    uid_list = list()
    try:
        con = _ldap_connection()
        con.simple_bind_s(AUTH_LDAP_BIND_DN, LDAP_ADMIN_PASSWD)
        dn = str('OU={0},DC={1},DC={2}'.format(
            AUTH_LDAP_OU,
            LDAP_DC_FIRST,
            LDAP_DC_SECOND
        ))
        ldap_result = con.search(dn, ldap.SCOPE_SUBTREE, 'cn=*', [str('uidNumber')])
        while 1:
            result_type, result_data = con.result(ldap_result, 0)
            if (result_data == []):
                break
            if 'uidNumber' in result_data[0][1]:
                uid_list.append(int(result_data[0][1]['uidNumber'][0]))


        uid_list.sort()
        return 1 + uid_list.pop()
    except:
        raise


def make_secret(password):
    """
    Encodes the given password as a base64 SSHA hash+salt buffer
    """
    salt = os.urandom(4)

    # hash the password and append the salt
    sha = hashlib.sha1(password)
    sha.update(salt)

    # create a base64 encoded string of the concatenated digest + salt
    digest_salt_b64 = "{0}{1}".format(sha.digest(), salt).encode('base64').strip()

    # now tag the digest above with the {SSHA} tag
    tagged_digest_salt = "{{SSHA}}{0}".format(digest_salt_b64)

    return tagged_digest_salt


def check_password(tagged_digest_salt, password):
    """
    Checks the OpenLDAP tagged digest against the given password
    """
    # the entire payload is base64-encoded
    assert tagged_digest_salt.startswith('{SSHA}')

    # strip off the hash label
    digest_salt_b64 = tagged_digest_salt[6:]

    # the password+salt buffer is also base64-encoded.  decode and split the
    # digest and salt
    digest_salt = digest_salt_b64.decode('base64')
    digest = digest_salt[:20]
    salt = digest_salt[20:]

    sha = hashlib.sha1(password)
    sha.update(salt)

    return digest == sha.digest()


def change_password(username, password):

    con = _ldap_connection()
    new_password = make_secret(password)

    try:
        logger.debug("try changing password in ldap")
        con.simple_bind_s(AUTH_LDAP_BIND_DN, LDAP_ADMIN_PASSWD)

        # For some reason, two MOD_REPLACE calls are necessary to change the password.
        # If only one call is performed, both the old and new password will work.
        mod_attrs = [(ldap.MOD_REPLACE, 'userPassword', [str(new_password)])]
        con.modify_s(
            str('CN={0},OU={1},DC={2},DC={3}'.format(
                username,
                AUTH_LDAP_OU,
                LDAP_DC_FIRST,
                LDAP_DC_SECOND
            )),
            mod_attrs
        )
    except:
        raise
    else:
        logger.info("Successfully changed password")
    finally:
        # Its nice to the server to disconnect and free resources when done
        logger.debug("closing connection to ldap")
        con.unbind_s()


# raw_password is the plaintext version of the password to
# be made secret ldap-style to be able to create user.
def create_user(user, raw_password):
    if not isinstance(user, get_user_model()):
        raise TypeError("Method only accepts objects of type User")

    con = _ldap_connection()

    new_password = make_secret(raw_password)

    try:
        logger.debug("try creating user in ldap")
        con.simple_bind_s(AUTH_LDAP_BIND_DN, LDAP_ADMIN_PASSWD)
        attrs = [
            ('objectclass', [str('posixAccount'), str('inetOrgPerson'), str('organizationalPerson'), str('person')]),
            ('cn', [str(user.username)]),
            ('uid', [str(user.username)]),
            ('gidNumber', [str(10000)]),
            ('uidNumber', [str(_get_next_uid())]),
            ('homeDirectory', [str('/home/{0}'.format(user.username))]),
            ('givenName', [str(user.first_name)]),
            ('sn', [str(user.last_name)]),
            ('userpassword', [str(new_password)]),
            ('mail', [str(user.email)]),
        ]
        dn = str('CN={0},OU={1},DC={2},DC={3}'.format(
            user.username,
            AUTH_LDAP_OU,
            LDAP_DC_FIRST,
            LDAP_DC_SECOND
        ))
        con.add_s(dn, attrs)
    except:
        raise
    else:
        logger.info("Successfully created user")
    finally:
        # Its nice to the server to disconnect and free resources when done
        logger.debug("closing connection to ldap")
        con.unbind_s()


def add_user_to_groups(user, groups=DEFAULT_USER_GROUPS):
    if not isinstance(user, get_user_model()):
        raise TypeError("Method only accepts objects of type User")

    con = _ldap_connection()
    try:
        logger.debug("try creating user in ldap")
        con.simple_bind_s(AUTH_LDAP_BIND_DN, LDAP_ADMIN_PASSWD)
        attrs = [
            (ldap.MOD_ADD, 'memberUid', [str(user.username)]),
        ]
        for group in groups:
            dn = str('CN={0},OU={1},DC={2},DC={3}'.format(
                group,
                AUTH_LDAP_GROUPS_OU,
                LDAP_DC_FIRST,
                LDAP_DC_SECOND
            ))
            con.modify_s(dn, attrs)
    except:
        raise
    else:
        logger.info("Successfully created user")
    finally:
        # Its nice to the server to disconnect and free resources when done
        logger.debug("closing connection to ldap")
        con.unbind_s()


def delete_user(user):
    if not isinstance(user, get_user_model()):
        raise TypeError("Method only accepts objects of type User")

    con = _ldap_connection()

    try:
        logger.debug("try deleting user in ldap")
        dn = str('UID={0},OU={1},DC={2},DC={3}'.format(
            user.username,
            AUTH_LDAP_OU,
            LDAP_DC_FIRST,
            LDAP_DC_SECOND
        ))
        con.delete_s(dn)
    except:
        raise
    else:
        logger.info("Successfully deleted user")
    finally:
        # Its nice to the server to disconnect and free resources when done
        logger.debug("closing connection to ldap")
        con.unbind_s()


class LDAPPasswordResetForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        from django.core.mail import send_mail
        UserModel = get_user_model()
        email = self.cleaned_data["email"]
        active_users = UserModel._default_manager.filter(
            email__iexact=email, is_active=True)
        for user in active_users:
            # Make sure that no email is sent to a user that actually has
            # a password marked as unusable

            # this check needs to be disabled because ldap users do not have a valid password set in django
            #if not user.has_usable_password():
                #continue
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            c = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            subject = loader.render_to_string(subject_template_name, c)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            email = loader.render_to_string(email_template_name, c)
            send_mail(subject, email, from_email, [user.email])


class LDAPSetPasswordForm(SetPasswordForm):

    new_password1 = PasswordField(label=_("Password"),
                                  help_text=_(mark_safe(PASSWORD_HELP_TEXT)),
                                  widget=forms.PasswordInput)
    new_password2 = PasswordField(label=_("Password confirmation"),
                                  help_text=_("Enter the same password as above, for verification."))

    def save(self, commit=True):
        #check if user also has an pw set in djangodb
        if self.user.has_usable_password():
            self.user.set_password(self.cleaned_data['new_password1'])

        try:
            #change ldap password
            change_password(self.user.username, self.cleaned_data['new_password1'])
        except ldap.LDAPError, e:
            if not self.user.is_staff and not self.user.is_superuser:
                raise

        if commit:
            self.user.save()
        return self.user


class LDAPPasswordChangeForm(LDAPSetPasswordForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. "
                                "Please enter it again."),
    })
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput)

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

LDAPPasswordChangeForm.base_fields = SortedDict([
    (k, LDAPPasswordChangeForm.base_fields[k])
    for k in ['old_password', 'new_password1', 'new_password2']
])
