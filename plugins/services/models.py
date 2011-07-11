import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from tagging.fields import TagField
from base.fields import SlugField
from managers import ServiceManager
from tinymce import models as tinymce_models
from meta.models import Meta as MetaTags
from module_meta import ServiceMeta

class Service(models.Model):
    guid = models.CharField(max_length=40)
    title = models.CharField(max_length=250)
    slug = SlugField(_('URL Path'), unique=True)  
    description = tinymce_models.HTMLField()
    location = models.CharField(max_length=500, blank=True)
    skills = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    education = models.TextField(blank=True)
    is_agency = models.BooleanField()
    list_type = models.CharField(max_length=50, default='regular')
    requested_duration = models.IntegerField(default=30)
    activation_dt = models.DateTimeField(null=True, blank=True)
    expiration_dt = models.DateTimeField(null=True, blank=True)
    resume_url = models.CharField(max_length=300, blank=True)
    syndicate = models.BooleanField(blank=True)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_address = models.CharField(max_length=50, blank=True)
    contact_address2 = models.CharField(max_length=50, blank=True)
    contact_city = models.CharField(max_length=50, blank=True)
    contact_state = models.CharField(max_length=50, blank=True)
    contact_zip_code = models.CharField(max_length=50, blank=True)
    contact_country = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_phone2 = models.CharField(max_length=50, blank=True)    
    contact_fax = models.CharField(max_length=50, blank=True)
    contact_email = models.CharField(max_length=300, blank=True)
    contact_website = models.CharField(max_length=300, blank=True)
    allow_anonymous_view = models.BooleanField(_("Public can view"))
    allow_user_view = models.BooleanField(_("Signed in user can view"))
    allow_member_view = models.BooleanField()
    allow_anonymous_edit = models.BooleanField()
    allow_user_edit = models.BooleanField(_("Signed in user can change"))
    allow_member_edit = models.BooleanField()
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(User, related_name="%(class)s_creator", editable=False, null=True)
    creator_username = models.CharField(max_length=50, null=True)
    owner = models.ForeignKey(User, related_name="%(class)s_owner", null=True)
    owner_username = models.CharField(max_length=50, null=True)
    status = models.BooleanField("Active", default=True)
    status_detail = models.CharField(max_length=50, default='active')
    
    meta = models.OneToOneField(MetaTags, null=True)
    tags = TagField(blank=True)
                 
    objects = ServiceManager()

    class Meta:
        permissions = (("view_service","Can view service"),)

    def get_meta(self, name):
        """
        This method is standard across all models that are
        related to the Meta model.  Used to generate dynamic
        meta information niche to this model.
        """
        return ServiceMeta().get_meta(self, name)

    @models.permalink
    def get_absolute_url(self):
        return ("service", [self.slug])
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.guid = str(uuid.uuid1())
        super(Service, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

    def is_pending(self):
        return self.status == 0 and self.status_detail == 'pending'

