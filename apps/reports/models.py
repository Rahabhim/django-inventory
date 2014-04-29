# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

"""
class ReportTopicManager(models.Manager):
    def by_request(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return self.all()
        else:
            return self.filter(active=True)

class ReportTopics(models.Model):
    " "" A piece of help, for any of our models, views, fields etc.
    "" "
    objects = ReportTopicManager()
    title = models.CharField(verbose_name=_(u'title'), max_length=100)
    mode = models.CharField(max_length=16, default='other', 
                choices=[('other', _('Other')), ('general', _("General")),
                        ('app', _('Application')),
                        ('view', _('View')), ('view_field', _('View field')),
                        ('model', _('Model')), ('field', _('Field')),
                        ])
    tkey = models.CharField(max_length=64, verbose_name=_("Key"))
    sequence = models.IntegerField(default=10, verbose_name=_("sequence"))
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_("created by"), on_delete=models.PROTECT)
    create_date = models.DateTimeField(verbose_name=_(u'create date'))
    write_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_("last changed by"), on_delete=models.PROTECT)
    write_date = models.DateTimeField(blank=True, null=True, verbose_name=_(u'last update date'))
    active = models.BooleanField(default=False, verbose_name=_(u'active'))
    content = models.TextField(null=True, blank=True, verbose_name=_(u'text'))
    
    # TODO:
    # lang =
    # keywords =
    

    class Meta:
        ordering = ('sequence', 'tkey')
        verbose_name = _(u'help topic')
        verbose_name_plural = _(u'help topic')
        unique_together = (('mode', 'tkey'),)

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('help_topic_view', [str(self.id)])

    @classmethod
    def rescanModels(self):
        pass
"""

#eof