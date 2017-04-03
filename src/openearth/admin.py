from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as OriginalUserAdmin
import ldap
from .forms import UserCreationForm
from django.contrib.auth.models import User
from openearth.actions import delete_selected, delete_selected_short_description
from openearth.forms import AdminPasswordChangeForm
from openearth.libs.auth import delete_user


class UserAdmin(OriginalUserAdmin):
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email')}
        ),
    )

    def delete_model(self, request, obj):
        # pre delete operations

        try:
            #delete user from ldap
            delete_user(obj)
            messages.add_message(request, messages.SUCCESS, 'Succesfully deleted User from ldap')
        except ldap.LDAPError, e:
            messages.add_message(request, messages.ERROR, "Deleting user in LDAP failed -> " + e.message['desc'])

        super(UserAdmin, self).delete_model(request, obj)
        # post delete operations

    def get_actions(self, request):
        actions = super(UserAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            actions['delete_selected'] = (
                delete_selected,
                'delete_selected',
                delete_selected_short_description
            )
        return actions

admin.site.unregister(User)
admin.site.register(User, UserAdmin)