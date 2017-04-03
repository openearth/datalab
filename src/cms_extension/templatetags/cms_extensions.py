from django import template
from cms import models

register = template.Library()


@register.simple_tag
def render_static_placeholder(placeholder):
    return models.StaticPlaceholder.objects.get_or_create(
        name=placeholder)[0].code


@register.simple_tag(takes_context=True)
def get_static_placeholder(context, placeholder):
    placeholder_code = models.StaticPlaceholder.objects.get_or_create(
        name=placeholder)[0].code
    context[placeholder] = placeholder_code
    return ''


@register.filter
def debug(o):
    import pprint
    d = dict()
    d.update(o.__dict__)

    return pprint.pformat(d)

