# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

class SavedReportManager(models.Manager):
    def by_request(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return self.all()
        else:
            return self.filter(owner=request.user)

class SavedReport(models.Model):
    """ Settings for a report, in JSON
    """
    objects = SavedReportManager()
    title = models.CharField(verbose_name=_(u'title'), max_length=64)
    rmodel = models.CharField(max_length=64)
    owner = models.ForeignKey('auth.User',verbose_name=_("owner"),
                            blank=True, null=True,
                            related_name='+', on_delete=models.CASCADE)
    params = models.TextField(null=True, blank=True, verbose_name=_(u'parameters'))

    class Meta:
        ordering = ('owner', 'title')
        verbose_name = _(u'saved report')
        verbose_name_plural = _(u'saved reports')
        unique_together = (('owner', 'title'),)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('reports_app_view') + ('?id=%d' % self.id)

#eof