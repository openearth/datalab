from django.views.generic import ListView
from openearth.apps.documentation.models import Documentation


class DocumentationOverView(ListView):
    model = Documentation
    context_object_name = 'documents'
    template_name = 'document_index.html'

    def get_queryset(self):
        return Documentation.get_published_documents()

