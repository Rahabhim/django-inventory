# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _

from models import HelpTopic
from datetime import datetime

class HelpTopicForm(forms.ModelForm):
    content = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 10}),
                label=_("Text"))
    class Meta:
        model = HelpTopic
        exclude = ('create_user', 'create_date', 'write_user', 'write_date')

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user
            self.instance.create_date = datetime.now()
        else:
            self.instance.write_user = user
            self.instance.write_date = datetime.now()


#eof