from pages.models import Page
from perms.utils import is_admin
from perms.forms import TendenciBaseForm
from django import forms
from tinymce.widgets import TinyMCE

class PageAdminForm(TendenciBaseForm):
    content = forms.CharField(required=False,
        widget=TinyMCE(attrs={'style':'width:100%'}, 
        mce_attrs={'storme_app_label':Page._meta.app_label, 
        'storme_model':Page._meta.module_name.lower()}))

    status_detail = forms.ChoiceField(
        choices=(('active','Active'),('inactive','Inactive'), ('pending','Pending'),))

    class Meta:
        model = Page
        fields = (
        'title',
        'slug',
        'content',
        'tags',
        'allow_anonymous_view',
        'syndicate',
        'status',
        'status_detail',
        )
        
    def __init__(self, *args, **kwargs): 
        super(PageAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['content'].widget.mce_attrs['app_instance_id'] = self.instance.pk
        else:
            self.fields['content'].widget.mce_attrs['app_instance_id'] = 0

class PageForm(TendenciBaseForm):

    content = forms.CharField(required=False,
        widget=TinyMCE(attrs={'style':'width:100%'}, 
        mce_attrs={'storme_app_label':Page._meta.app_label, 
        'storme_model':Page._meta.module_name.lower()}))

    status_detail = forms.ChoiceField(
        choices=(('active','Active'),('inactive','Inactive'), ('pending','Pending'),))
        
    class Meta:
        model = Page
        fields = (
        'title',
        'slug',
        'content',
        'tags',
        'allow_anonymous_view',
        'syndicate',
        'status',
        'status_detail',
        )

        fieldsets = [('Page Information', {
                      'fields': ['title',
                                 'slug',
                                 'content',
                                 'tags',
                                 ],
                      'legend': ''
                      }),
                      ('Permissions', {
                      'fields': ['allow_anonymous_view',
                                 'user_perms',
                                 'group_perms',
                                 ],
                      'classes': ['permissions'],
                      }),
                     ('Administrator Only', {
                      'fields': ['syndicate',
                                 'status',
                                 'status_detail'], 
                      'classes': ['admin-only'],
                    })]
      
    def __init__(self, *args, **kwargs): 
        super(PageForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['content'].widget.mce_attrs['app_instance_id'] = self.instance.pk
        else:
            self.fields['content'].widget.mce_attrs['app_instance_id'] = 0

        if not is_admin(self.user):
            if 'syndicate' in self.fields: self.fields.pop('syndicate')
            if 'status' in self.fields: self.fields.pop('status')
            if 'status_detail' in self.fields: self.fields.pop('status_detail')