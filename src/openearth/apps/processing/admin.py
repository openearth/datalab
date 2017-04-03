from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
import models
from forms import JobAdminForm, ProcessingJobImageAdminForm
from tags_input import admin as tags_input_admin
import reversion


class ExtensionAdmin(reversion.VersionAdmin):
    list_display = ('extension', 'name')
    search_fields = ('name', 'extension')
    prepopulated_fields = {'name': ('extension',)}


class ProcessingJobImageAdmin(tags_input_admin.TagsInputAdmin):
    form = ProcessingJobImageAdminForm


class ProcessingJobResultAdmin(reversion.VersionAdmin):
    list_display = ('job', 'file')


class ProcessingJobResultInlineAdmin(admin.TabularInline):
    model = models.ProcessingJobResult
    extra = 0

    can_delete = False
    readonly_fields = 'committed',


class ProcessingJobAdmin(reversion.VersionAdmin):

    def script_link(self, instance):
        name = instance.script
        if instance.script_revision:
            name += ' at revision: %s' % instance.script_revision
        return '<a target="_blank" href="%s">%s</a>' % (
            instance.get_script_url(), name)
    script_link.short_description = 'Script'
    script_link.allow_tags = True

    list_display = ('__unicode__', 'status', 'start', 'created_date',
                    'environment')
    list_filter = ('status', 'environment', 'environment__author__username')
    search_fields = ('uuid', 'environment__name',
                     'environment__author__username')
    readonly_fields = ('status', 'start', 'created_date', 'environment',
                       'script_link')

    fieldsets = (
        (None, {
            'fields': ('status', 'start', 'created_date', 'environment',
                       'script_link')
        }),
        ('Terminal output', {
            'classes': ('collapse',),
            'fields': ('terminal',)
        }),
    )

    inlines = [ProcessingJobResultInlineAdmin]
    form = JobAdminForm

    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super(ProcessingJobAdmin, self).get_form(request, obj,
                                                             **kwargs)

        class ModelFormMetaClass(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return ModelFormMetaClass


class ProcessingJobInlineAdmin(admin.TabularInline):
    def get_status(self, obj):
        if obj.pk:
            return obj.get_status_display()
        else:
            return '----'

    get_status.short_description = _('status')

    readonly_fields = ('get_status', 'created_date',)
    date_hierarchy = 'created_date'
    fields = ('start', 'auto_commit', 'get_status', 'created_date',)
    model = models.ProcessingJob
    extra = 0


class ProcessingEnvironmentAdmin(reversion.VersionAdmin):
    exclude = ('author',)
    readonly_fields = ('created_date',)
    list_display = ('name', 'created_date', 'author')
    inlines = [ProcessingJobInlineAdmin]

    def has_change_permission(self, request, obj=None):
        has_class_permission = super(ProcessingEnvironmentAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.author.id:
            return False
        return True

    def queryset(self, request):
        if request.user.is_superuser:
            return models.ProcessingEnvironment.objects.all()
        return models.ProcessingEnvironment.objects.filter(author=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        obj.save()

admin.site.register(models.Extension, ExtensionAdmin)
admin.site.register(models.ProcessingEnvironment, ProcessingEnvironmentAdmin)
admin.site.register(models.ProcessingJob, ProcessingJobAdmin)
admin.site.register(models.ProcessingJobResult, ProcessingJobResultAdmin)
admin.site.register(models.ProcessingJobImage, ProcessingJobImageAdmin)
