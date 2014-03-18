from django.template import Library

from photos.models import GenericPhoto

register = Library()

@register.filter
#@stringfilter
def get_photos_for_object(value):
    return GenericPhoto.objects.photos_for_object(value)
