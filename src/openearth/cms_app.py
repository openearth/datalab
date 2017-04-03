from cms import app_base
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _


class Openearth(app_base.CMSApp):
    name = _('Openearth')
    urls = ['openearth.urls']

apphook_pool.register(Openearth)

