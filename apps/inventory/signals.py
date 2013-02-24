# -*- encoding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver
from models import Inventory

from assets.models import Item
import logging

logger = logging.getLogger('apps.inventory')

def __get_changelog(sender, instance, old_record=True):
    new_instance = instance

    if old_record:
        try:
            old_instance = sender.objects.get(pk=new_instance.id)
        except:
            old_record = False

    change_log = ''

    for field in new_instance.__class__._meta.fields:# + new_instance.__class__._meta.many_to_many:
        new_value = unicode(getattr(new_instance,field.name))

        if old_record:
            old_value = unicode(getattr(old_instance,field.name))
        else:
            old_value = None

        if not old_value == new_value:
            if new_value:
                change_log += "field: %s\n===========\n" % unicode(field.verbose_name)
                if old_value:
                    change_log += "old value:\n%s\n\n" % (old_value)
                change_log += "new value:\n%s\n===========\n\n" % (new_value)

    return change_log


@receiver(post_save, sender=Inventory, dispatch_uid='139i439')
def post_save_inventory(sender, instance=None, created=False, raw=False,  **kwargs):
    """ create the locations, after a department has been saved
    """
    if instance is not None and created and not raw:
        logger.debug("New inventory %s, fill it with items.", instance)
        if instance.items.exists():
            return

        for item in Item.objects.filter(location=instance.location):
            instance.items.create(asset=item, quantity=1)

        logger.debug("Created %d items in inventory", instance.items.count())

#eof
