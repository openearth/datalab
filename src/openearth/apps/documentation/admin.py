from django.contrib import admin
from openearth.apps.documentation.models import Documentation


class DocumentationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'published')

admin.site.register(Documentation, DocumentationAdmin)
