# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.forms.util import flatatt
from models import HelpTopic
from datetime import datetime


class HTMLArea(forms.Textarea):

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        self.html_id = final_attrs.pop('id', name)
        context = {
            'name': name,
            'html_id': self.html_id,
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),
            'value': mark_safe(force_unicode(value)), # yes, unescaped html
        }
        return mark_safe(render_to_string('form_field_wysihtml5.html', context))

class HelpTopicForm(forms.ModelForm):
    content = forms.CharField(required=False, widget=HTMLArea(),
                label=_("Text"))
    class Meta:
        model = HelpTopic
        exclude = ('create_user', 'create_date', 'write_user', 'write_date')

    class Media:
        # "css/bootstrap.min.css", conflicts
        css = {'all': ( "css/wysihtml5.css",
                    "css/font-awesome.min.css", "css/form_wysihtml5.css"), }
        js = ( 'js/wysihtml5.min.js', 'js/advanced.js')

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user
            self.instance.create_date = datetime.now()
        else:
            self.instance.write_user = user
            self.instance.write_date = datetime.now()


#eof