import uuid
import re
from datetime import datetime, timedelta
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from tagging.fields import TagField
from base.fields import SlugField
from timezones.fields import TimeZoneField
from perms.models import TendenciBaseModel 
from directories.managers import DirectoryManager
from tinymce import models as tinymce_models
from meta.models import Meta as MetaTags
from directories.module_meta import DirectoryMeta
from entities.models import Entity
from invoices.models import Invoice
from perms.utils import is_admin

def file_directory(instance, filename):
    filename = re.sub(r'[^a-zA-Z0-9._]+', '-', filename)
    return 'directories/%s' % (filename)

class Directory(TendenciBaseModel):
 
    guid = models.CharField(max_length=40)
    slug = SlugField(_('URL Path'), unique=True)
    timezone = TimeZoneField(_('Time Zone'))
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    body = tinymce_models.HTMLField()
    source = models.CharField(max_length=300, blank=True)
    logo = models.FileField(max_length=260, upload_to=file_directory, 
                            help_text=_('Company logo. Only jpg, gif, or png images.'), 
                            blank=True)
    
    first_name = models.CharField(_('First Name'), max_length=100, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True)
    address = models.CharField(_('Address'), max_length=100, blank=True)
    address2 = models.CharField(_('Address 2'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=50, blank=True)
    state = models.CharField(_('State'), max_length=50, blank=True)
    zip_code = models.CharField(_('Zip Code'), max_length=50, blank=True)
    country = models.CharField(_('Country'), max_length=50, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    phone2 = models.CharField(_('Phone 2'), max_length=50, blank=True)
    fax = models.CharField(_('Fax'), max_length=50, blank=True)
    email = models.CharField(_('Email'), max_length=120, blank=True)
    email2 = models.CharField(_('Email 2'), max_length=120, blank=True)
    website = models.CharField(max_length=300, blank=True)
     
    list_type = models.CharField(_('List Type'), max_length=50, blank=True)
    requested_duration = models.IntegerField(_('Requested Duration'), default=0)
    activation_dt = models.DateTimeField(_('Activation Date/Time'), null=True, blank=True)
    expiration_dt = models.DateTimeField(_('Expiration Date/Time'), null=True, blank=True)
    invoice = models.ForeignKey(Invoice, blank=True, null=True) 
    payment_method = models.CharField(_('Payment Method'), max_length=50, blank=True)

    syndicate = models.BooleanField(_('Include in RSS feed'),)
    design_notes = models.TextField(_('Design Notes'), blank=True)
    admin_notes = models.TextField(_('Admin Notes'), blank=True)
    tags = TagField(blank=True)
   
    # for podcast feeds
    enclosure_url = models.CharField(_('Enclosure URL'), max_length=500, blank=True)
    enclosure_type = models.CharField(_('Enclosure Type'), max_length=120, blank=True)
    enclosure_length = models.IntegerField(_('Enclosure Length'), default=0)

    entity = models.ForeignKey(Entity, null=True, blank=True)
    
    # html-meta tags
    meta = models.OneToOneField(MetaTags, null=True)

    objects = DirectoryManager()

    class Meta:
        permissions = (("view_directory","Can view directory"),)
        verbose_name_plural = 'directories'

    def get_meta(self, name):
        """
        This method is standard across all models that are
        related to the Meta model.  Used to generate dynamic
        methods coupled to this instance.
        """    
        return DirectoryMeta().get_meta(self, name)
    
    @models.permalink
    def get_absolute_url(self):
        return ("directory", [self.slug])

    def __unicode__(self):
        return self.headline
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.guid = str(uuid.uuid1())
            
        super(Directory, self).save(*args, **kwargs)

    # Called by payments_pop_by_invoice_user in Payment model.
    def get_payment_description(self, inv):
        """
        The description will be sent to payment gateway and displayed on invoice.
        If not supplied, the default description will be generated.
        """
        return 'Tendenci Invoice %d for Directory: %s (%d).' % (
            inv.id,
            self.headline,
            inv.object_id,
        )

    def make_acct_entries(self, user, inv, amount, **kwargs):
        """
        Make the accounting entries for the directory sale
        """
        from accountings.models import Acct, AcctEntry, AcctTran
        from accountings.utils import make_acct_entries_initial, make_acct_entries_closing

        ae = AcctEntry.objects.create_acct_entry(user, 'invoice', inv.id)
        if not inv.is_tendered:
            make_acct_entries_initial(user, ae, amount)
        else:
            # payment has now been received
            make_acct_entries_closing(user, ae, amount)

            # #CREDIT directory SALES
            acct_number = self.get_acct_number()
            acct = Acct.objects.get(account_number=acct_number)
            AcctTran.objects.create_acct_tran(user, ae, acct, amount*(-1))

    def get_acct_number(self, discount=False):
        if discount:
            return 464400
        else:
            return 404400

    def auto_update_paid_object(self, request, payment):
        """
        Update the object after online payment is received.
        """
        if not is_admin(request.user):
            self.status_detail = 'paid - pending approval'
        self.expiration_dt = self.activation_dt + timedelta(days=self.requested_duration)
        self.save()

    def age(self):
        return datetime.now() - self.create_dt

class DirectoryPricing(models.Model):
    guid = models.CharField(max_length=40)
    duration = models.IntegerField(blank=True)
    regular_price =models.DecimalField(max_digits=15, decimal_places=2, blank=True, default=0)
    premium_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True, default=0)
    category_threshold = models.IntegerField(blank=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(User, related_name="directory_pricing_creator",  null=True)
    creator_username = models.CharField(max_length=50, null=True)
    owner = models.ForeignKey(User, related_name="directory_pricing_owner", null=True)
    owner_username = models.CharField(max_length=50, null=True)
    status = models.BooleanField(default=True)

    class Meta:
        permissions = (("view_directory_pricing", "Can view directory pricing"),)
    
    def save(self, user=None, *args, **kwargs):
        if not self.id:
            self.guid = str(uuid.uuid1())
            if user and user.id:
                self.creator=user
                self.creator_username=user.username
        if user and user.id:
            self.owner=user
            self.owner_username=user.username
        if not self.regular_price: self.regular_price = 0
        if not self.premium_price: self.premium_price = 0
        if not self.category_threshold: self.category_threshold = 0
            
        super(DirectoryPricing, self).save(*args, **kwargs)

