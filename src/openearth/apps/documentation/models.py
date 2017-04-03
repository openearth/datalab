from django.db import models
from django.utils.translation import ugettext_lazy as _


class Documentation(models.Model):
    """
    This model is responsible for keeping track of the documentation
    """

    class Meta:
        verbose_name_plural = _("Documentation")

    name = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
        help_text=_('Name of the document')
    )
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Description of the document')
    )
    file = models.FileField(
        upload_to="docs/",
        verbose_name=_('Document to share'),
        help_text=_('Upload your document here. Use the pdf format.')
    )
    published = models.BooleanField(
        default=False,
        verbose_name=_('Published'),
        help_text=_('Users are able to download documents when a document has been published.')
    )

    @staticmethod
    def get_published_documents():
        return Documentation.objects.filter(published=True)