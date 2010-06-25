import uuid
# guid = str(uuid.uuid1()) # based on the host ID and current time
#guid = str(uuid.uuid4())) # make a random UUID
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db.models import Manager
from perms.utils import is_admin

class InvoiceManager(Manager):
    def create_invoice(self, user, **kwargs):
        return self.create(title=kwargs.get('title', ''), 
                           estimate=kwargs.get('estimate', True),
                           status=kwargs.get('status', True), 
                           status_detail=kwargs.get('status_detail', 'estimate'),
                           invoice_object_type=kwargs.get('invoice_object_type', ''),
                           invoice_object_type_id=kwargs.get('invoice_object_type_id', 0),
                           subtotal=kwargs.get('subtotal', 0),
                           total=kwargs.get('total', 0),
                           balance=kwargs.get('balance', 0),
                           creator=user, 
                           creator_username=user.username,
                           owner=user, 
                           owner_username=user.username)

class Invoice(models.Model):
    guid = models.CharField(max_length=50)
    invoice_object_type = models.CharField(_('object_type'), max_length=50, blank=True, null=True)
    invoice_object_type_id = models.IntegerField(blank=True, null=True)
    job_id = models.IntegerField(null=True)
    title = models.CharField(max_length=150, blank=True, null=True)
    tender_date = models.DateTimeField(null=True)
    #session_id = models.CharField(max_length=40, null=True) # used to replace rmid in T4
    # priceasofdate and invoice_number seem like not being used in T4
    #priceasofdate = models.DateTimeField(null=True)
    #invoice_number = models.IntegerField(null=True)
    bill_to = models.CharField(max_length=120, blank=True)
    bill_to_first_name = models.CharField(max_length=100, blank=True, null=True)
    bill_to_last_name = models.CharField(max_length=100, blank=True, null=True)
    bill_to_company = models.CharField(max_length=50, blank=True, null=True)
    bill_to_address = models.CharField(max_length=100, blank=True, null=True)
    bill_to_city = models.CharField(max_length=50, blank=True, null=True)
    bill_to_state = models.CharField(max_length=50, blank=True, null=True)
    bill_to_zip_code = models.CharField(max_length=20, blank=True, null=True)
    bill_to_country = models.CharField(max_length=50, blank=True, null=True)
    bill_to_phone = models.CharField(max_length=50, blank=True, null=True)
    bill_to_fax = models.CharField(max_length=50, blank=True, null=True)
    bill_to_email = models.CharField(max_length=100, blank=True, null=True)
    ship_to = models.CharField(max_length=120, blank=True)
    ship_to_first_name = models.CharField(max_length=50, blank=True)
    ship_to_last_name = models.CharField(max_length=50, blank=True)
    ship_to_company = models.CharField(max_length=50, blank=True)
    ship_to_address = models.CharField(max_length=100, blank=True)
    ship_to_city = models.CharField(max_length=50, blank=True)
    ship_to_state = models.CharField(max_length=50, blank=True)
    ship_to_zip_code = models.CharField(max_length=20, blank=True)
    ship_to_country = models.CharField(max_length=50, blank=True)
    ship_to_phone = models.CharField(max_length=50, blank=True, null=True)
    ship_to_fax = models.CharField(max_length=50, blank=True, null=True)
    ship_to_email = models.CharField(max_length=100, blank=True, null=True)
    ship_to_address_type = models.CharField(max_length=50, blank=True, null=True)
    receip= models.BooleanField(default=0)
    gift = models.BooleanField(default=0)
    arrival_date_time = models.DateTimeField(blank=True, null=True)   
    greeting = models.CharField(max_length=500, blank=True, null=True)   
    instructions = models.CharField(max_length=500, blank=True, null=True)   
    po = models.CharField(max_length=50, blank=True)
    terms = models.CharField(max_length=50, blank=True)
    due_date = models.DateTimeField()
    ship_date = models.DateTimeField()
    ship_via = models.CharField(max_length=50, blank=True)
    fob = models.CharField(max_length=50, blank=True, null=True)
    project = models.CharField(max_length=50, blank=True, null=True)   
    other = models.CharField(max_length=120, blank=True, null=True)
    message = models.CharField(max_length=150, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, blank=True)
    shipping = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    shipping_surcharge =models.DecimalField(max_digits=6, decimal_places=2, default=0)
    box_and_packing = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tax_exempt =models.BooleanField(default=1)
    tax_exemptid = models.CharField(max_length=50, blank=True, null=True)  
    tax_rate = models.FloatField(blank=True, default=0)
    taxable = models.BooleanField(default=0)
    tax = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    variance = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, blank=True)
    payments_credits = models.DecimalField(max_digits=15, decimal_places=2, blank=True, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, blank=True, default=0)
    estimate = models.BooleanField(default=1)
    disclaimer = models.CharField(max_length=150, blank=True, null=True)
    variance_notes = models.TextField(max_length=1000, blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(User, related_name="invoice_creator",  null=True)
    creator_username = models.CharField(max_length=50, null=True)
    owner = models.ForeignKey(User, related_name="invoice_owner", null=True)
    owner_username = models.CharField(max_length=50, null=True)
    status_detail = models.CharField(max_length=50, default='estimate')
    status = models.BooleanField(default=True)
    
    objects = InvoiceManager()
    
    def __unicode__(self):
        return u'Invoice: %s' % (self.title)
    
    @models.permalink
    def get_absolute_url(self):
        return ('invoice.view', [self.id])
    
    def save(self, user=None):
        if not self.id:
            self.guid = str(uuid.uuid1())
            if user and user.id:
                self.creator=user
                self.creator_username=user.username
        if user and user.id:
            self.owner=user
            self.owner_username=user.username
            
        super(self.__class__, self).save()
    
    @property
    def is_tendered(self):
        boo = False
        if self.id > 0:
            if self.status_detail.lower() == 'tendered':
                boo = True
        return boo
    
    def tender(self, user):
        from accountings.utils import make_acct_entries
        """ mark it as tendered if we have records """ 
        if not self.is_tendered:
            # make accounting entry
            make_acct_entries(user, self, self.total)
            
            self.estimate = False
            self.status_detail = 'tendered'
            self.status = 1
            self.tender_date = datetime.now()
            self.save()
        return True
            
    
    # if this invoice allows view by user2_compare
    def allow_view_by(self, user2_compare, guid=''):
        boo = False
        if is_admin(user2_compare):
            boo = True
        else: 
            if user2_compare and user2_compare.id > 0:
                if self.creator == user2_compare or self.owner == user2_compare:
                    if self.status == 1:
                        boo = True
            else: 
                # anonymous user
                if self.guid and self.guid == guid:
                    boo = True
            
        return boo
    
    def allow_payment_by(self, user2_compare,  guid=''):
        return self.allow_view_by(user2_compare,  guid)
    
    # if this invoice allows edit by user2_compare
    def allow_edit_by(self, user2_compare, guid=''):
        boo = False
        if user2_compare.is_superuser:
            boo = True
        else:
            if user2_compare and user2_compare.id > 0: 
                if self.creator == user2_compare or self.owner == user2_compare:
                    if self.status == 1:
                        # user can only edit a non-tendered invoice
                        if not self.is_tendered:
                            boo = True
            else:
                if self.guid and self.guid == guid: # for anonymous user
                    if self.status == 1 and not self.is_tendered:  
                        boo = True
        return boo
    
    def assign_make_payment_info(self, user, make_payment, **kwargs):
        self.title = "Make Payment Invoice"
        self.invoice_date = datetime.now()
        self.bill_to = make_payment.first_name + ' ' + make_payment.last_name
        self.bill_to_first_name = make_payment.first_name
        self.bill_to_last_name = make_payment.last_name
        self.bill_to_company = make_payment.company
        self.bill_to_address = make_payment.address
        self.bill_to_city = make_payment.city
        self.bill_to_state = make_payment.state
        self.bill_to_zip_code = make_payment.zip_code
        self.bill_to_country = make_payment.country
        self.bill_to_phone = make_payment.phone
        #self.bill_to_fax = make_payment.fax
        self.bill_to_email = make_payment.email
        self.ship_to = make_payment.first_name + ' ' + make_payment.last_name
        self.ship_to_first_name = make_payment.first_name
        self.ship_to_last_name = make_payment.last_name
        self.ship_to_company = make_payment.company
        self.ship_to_address = make_payment.address
        self.ship_to_city = make_payment.city
        self.ship_to_state = make_payment.state
        self.ship_to_zip_code = make_payment.zip_code
        self.ship_to_country = make_payment.country
        self.ship_to_phone = make_payment.phone
        #self.ship_to_fax = make_payment.fax
        self.ship_to_email =make_payment.email
        self.terms = "Due on Receipt"
        self.due_date = datetime.now()
        self.ship_date = datetime.now()
        self.message = 'Thank You.'
        self.status = True
     
    # this function is to make accounting entries    
    def make_payment(self, user, amount):
        from accountings.utils import make_acct_entries
        if self.is_tendered:
            self.balance -= amount
            self.payments_credits += amount
            self.save()
            # Make the accounting entries here
            make_acct_entries(user, self, amount)
        
        
        