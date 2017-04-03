# vim: set fileencoding=utf-8 :
import models
from django.contrib import admin
from django import shortcuts
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.template.response import TemplateResponse

from system import utils

class DiskAdmin(admin.ModelAdmin):
    def has_add_permission(*args, **kwargs):
        return False

    def has_delete_permission(*args, **kwargs):
        return False

    def changelist_view(self, request):
        opts = self.model._meta
        app_label = opts.app_label

        mounts = utils.get_disk_usages()
        context = {
            'module_name': force_text(opts.verbose_name_plural),
            'selection_note': _('0 of %(cnt)s selected')
                % {'cnt': len(mounts)},
            'selection_note_all': _('0 of %(cnt)s selected')
                % {'cnt': len(mounts)},
            'title': 'System Disks',
            'mounts': mounts,
            'media': self.media,
            'has_add_permission': self.has_add_permission(request),
            'opts': opts,
            'app_label': app_label,
            'action_form': None,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
            'preserved_filters': self.get_preserved_filters(request),
        }

        # return shortcuts.render(request, 'admin/system/disks.html', context)
        return TemplateResponse(request, self.change_list_template or [
            'admin/%s/%s/change_list.html' % (app_label, opts.model_name),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ], context, current_app=self.admin_site.name)


admin.site.register(models.Disk, DiskAdmin)

