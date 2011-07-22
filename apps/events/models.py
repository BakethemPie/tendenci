import uuid
from hashlib import md5
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.aggregates import Sum
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.core.exceptions import ObjectDoesNotExist

from timezones.fields import TimeZoneField
from entities.models import Entity
from events.managers import EventManager, RegistrantManager, EventTypeManager
from perms.models import TendenciBaseModel
from meta.models import Meta as MetaTags
from events.module_meta import EventMeta
from user_groups.models import Group

from invoices.models import Invoice
from files.models import File
from site_settings.utils import get_setting
from payments.models import PaymentMethod as GlobalPaymentMethod


class TypeColorSet(models.Model):
    """
    Colors representing a type [color-scheme]
    The values can be hex or literal color names
    """
    fg_color = models.CharField(max_length=20)
    bg_color = models.CharField(max_length=20)
    border_color = models.CharField(max_length=20)

    def __unicode__(self):
        return '%s #%s' % (self.pk, self.bg_color)


class Type(models.Model):
    
    """
    Types is a way of grouping events
    An event can only be one type
    A type can have multiple events
    """
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, editable=False)
    color_set = models.ForeignKey('TypeColorSet')

    objects = EventTypeManager()

    @property
    def fg_color(self):
        return '#%s' % self.color_set.fg_color
    @property
    def bg_color(self):
        return '#%s' % self.color_set.bg_color
    @property
    def border_color(self):
        return '#%s' % self.color_set.border_color

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Type, self).save(*args, **kwargs)

class Place(models.Model):
    """
    Event Place (location)
    An event can only be in one place
    A place can be used for multiple events
    """
    name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    # offline location
    address = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=150, blank=True)
    state = models.CharField(max_length=150, blank=True)
    zip = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=150, blank=True)

    # online location
    url = models.URLField(blank=True)

    def __unicode__(self):
        str_place = '%s %s %s %s %s' % (
            self.name, self.address, ', '.join(self.city_state()), self.zip, self.country)
        return unicode(str_place.strip())

    def city_state(self):
        return [s for s in (self.city, self.state) if s]


class Registrant(models.Model):
    """
    Event registrant.
    An event can have multiple registrants.
    A registrant can go to multiple events.
    A registrant is static information.
    The names do not change nor does their information
    This is the information that was used while registering
    """
    registration = models.ForeignKey('Registration')
    user = models.ForeignKey(User, blank=True, null=True)
    amount = models.DecimalField(_('Amount'), max_digits=21, decimal_places=2, blank=True, default=0)
    
    name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    mail_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=50)
    country = models.CharField(max_length=100)

    phone = models.CharField(max_length=50)
    email = models.CharField(max_length=100)
    groups = models.CharField(max_length=100)

    position_title = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)

    cancel_dt = models.DateTimeField(editable=False, null=True)

    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
    
    objects = RegistrantManager()

    @property
    def lastname_firstname(self):
        fn = self.first_name or None
        ln = self.last_name or None
        
        if fn and ln:
            return ', '.join([ln, fn])
        return fn or ln

    @classmethod
    def event_registrants(cls, event=None):

        return cls.objects.filter(
            registration__event = event,
            cancel_dt = None,
        )
        
    @property
    def additional_registrants(self):
        # additional registrants on the same invoice
        return self.registration.registrant_set.filter(cancel_dt = None).exclude(id=self.id).order_by('id')

    @property
    def hash(self):
        return md5(".".join([str(self.registration.event.pk), str(self.pk)])).hexdigest()

    @property
    def old_hash1(self):
        """
        Deprecated: Remove after 7/01/2011
        """
        return md5(".".join([str(self.registration.event.pk), self.email, str(self.pk)])).hexdigest()

    @property
    def old_hash2(self):
        """
        Deprecated: Remove after 7/01/2011
        """
        return md5(".".join([str(self.registration.event.pk), self.email])).hexdigest()

    @models.permalink
    def hash_url(self):
        return ('event.registration_confirmation', [self.registration.event.pk, self.hash])

    class Meta:
        permissions = (("view_registrant","Can view registrant"),)

    @models.permalink
    def get_absolute_url(self):
        return ('event.registration_confirmation', [self.registration.event.pk, self.pk])

    def reg8n_status(self):
        """
        Returns string status.
        """
        config = self.registration.event.registration_configuration

        balance = self.registration.invoice.balance
        payment_required = config.payment_required

        if self.cancel_dt:
            return 'cancelled'

        if balance > 0:
            if payment_required:
                return 'payment-required'
            else:
                return 'registered-with-balance'
        else:
            return 'registered'


class RegistrationConfiguration(models.Model):
    """
    Event registration
    Extends the event model
    """
    # TODO: use shorter name
    # TODO: do not use fixtures, use RAWSQL to prepopulate
    # TODO: set widget here instead of within form class
    payment_method = models.ManyToManyField(GlobalPaymentMethod)    
    payment_required = models.BooleanField(help_text='A payment required before registration is accepted.')
    
    limit = models.IntegerField(_('Registration Limit'), default=0)
    enabled = models.BooleanField(_('Enable Registration'), default=False)

    is_guest_price = models.BooleanField(_('Guests Pay Registrant Price'), default=False)

    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    @property
    def can_pay_online(self):
        """
        Check online payment dependencies.
        Return boolean.
        """
        has_method = GlobalPaymentMethod.objects.filter(is_online=True).exists()
        has_account = get_setting('site', 'global', 'merchantaccount') is not ''
        has_api = settings.MERCHANT_LOGIN is not ''

        return all([has_method, has_account, has_api])


class RegConfPricing(models.Model):
    """
    Registration configuration pricing
    """
    reg_conf = models.ForeignKey(RegistrationConfiguration, blank=True, null=True)

    title = models.CharField(max_length=50, blank=True)
    quantity = models.IntegerField(_('Number of attendees'), default=1, blank=True, help_text='Total people included in each registration for this pricing group. Ex: Table or Team.')
    group = models.ForeignKey(Group, blank=True, null=True)

    early_price = models.DecimalField(_('Early Price'), max_digits=21, decimal_places=2, default=0)
    regular_price = models.DecimalField(_('Regular Price'), max_digits=21, decimal_places=2, default=0)
    late_price = models.DecimalField(_('Late Price'), max_digits=21, decimal_places=2, default=0)
    
    early_dt = models.DateTimeField(_('Early Registration Starts'), default=datetime.now())
    regular_dt = models.DateTimeField(_('Regular Registration Starts'), default=datetime.now()+timedelta(hours=2))
    late_dt = models.DateTimeField(_('Late Registration Starts'), default=datetime.now()+timedelta(hours=4))
    end_dt = models.DateTimeField(_('Registration Ends'), default=datetime.now()+timedelta(hours=6))

    allow_anonymous = models.BooleanField(_("Public can use"))
    allow_user = models.BooleanField(_("Signed in user can use"))
    allow_member = models.BooleanField(_("All members can use"))

    def __unicode__(self):
        if self.title:
            return '%s' % self.title
        return '%s' % self.pk

    def __init__(self, *args, **kwargs):
        super(RegConfPricing, self).__init__(*args, **kwargs)
        self.PERIODS = {
            'early': (self.early_dt, self.regular_dt),
            'regular': (self.regular_dt, self.late_dt),
            'late': (self.late_dt, self.end_dt),
        }

    def available(self):
        if not self.reg_conf.enabled:
            return False
        if hasattr(self, 'event'):
            if datetime.now() > self.event.end_dt:
                return False
        return True

    @property
    def price(self):
        price = 0.00
        for period in self.PERIODS:
            if self.PERIODS[period][0] <= datetime.now() <= self.PERIODS[period][1]:
                price = self.price_from_period(period)
        return price

    def price_from_period(self, period):
        if period in self.PERIODS:
            return getattr(self, '%s_price' % period)
        else: 
            return None

    @property
    def registration_has_started(self):
        has_started = []
        for period in self.PERIODS:
            if datetime.now() >= self.PERIODS[period][0]:
                has_started.append(True)
            has_started.append(False)
        return any(has_started)

    @property
    def is_open(self):
        status = [
            self.reg_conf.enabled,
            self.within_time,
        ]
        return all(status)

    @property
    def within_time(self):
        for period in self.PERIODS:
            if self.PERIODS[period][0] <= datetime.now() <= self.PERIODS[period][1]:
                return True
        return False


class Registration(models.Model):

    guid = models.TextField(max_length=40, editable=False)
    note = models.TextField(blank=True)
    event = models.ForeignKey('Event')
    invoice = models.ForeignKey(Invoice, blank=True, null=True)
    reg_conf_price = models.ForeignKey(RegConfPricing, null=True)
    reminder = models.BooleanField(default=False)
    
    # TODO: Payment-Method must be soft-deleted
    # so that it may always be referenced
    payment_method = models.ForeignKey(GlobalPaymentMethod, null=True)
    amount_paid = models.DecimalField(_('Amount Paid'), max_digits=21, decimal_places=2)

    creator = models.ForeignKey(User, related_name='created_registrations', null=True)
    owner = models.ForeignKey(User, related_name='owned_registrations', null=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (("view_registration","Can view registration"),)

    def __unicode__(self):
        return 'Registration - %s' % self.event.title

    @property
    def hash(self):
        return md5(".".join([str(self.event.pk), str(self.pk)])).hexdigest()

    # Called by payments_pop_by_invoice_user in Payment model.
    def get_payment_description(self, inv):
        """
        The description will be sent to payment gateway and displayed on invoice.
        If not supplied, the default description will be generated.
        """
        return 'Tendenci Invoice %d for Event (%d): %s (Reg# %d)' % (
            inv.id,
            self.event.pk,
            self.event.title,
            inv.object_id,
        )
        
    def make_acct_entries(self, user, inv, amount, **kwargs):
        """
        Make the accounting entries for the event sale
        """
        from accountings.models import Acct, AcctEntry, AcctTran
        from accountings.utils import make_acct_entries_initial, make_acct_entries_closing
        
        ae = AcctEntry.objects.create_acct_entry(user, 'invoice', inv.id)
        if not inv.is_tendered:
            make_acct_entries_initial(user, ae, amount)
        else:
            # payment has now been received
            make_acct_entries_closing(user, ae, amount)
            
            # #CREDIT event SALES
            acct_number = self.get_acct_number()
            acct = Acct.objects.get(account_number=acct_number)
            AcctTran.objects.create_acct_tran(user, ae, acct, amount*(-1))
    
    # to lookup for the number, go to /accountings/account_numbers/        
    def get_acct_number(self, discount=False):
        if discount:
            return 462000
        else:
            return 402000

    def auto_update_paid_object(self, request, payment):
        """
        Update the object after online payment is received.
        """
        from datetime import datetime
        try:
            from notification import models as notification
        except:
            notification = None
        from perms.utils import get_notice_recipients

        site_label = get_setting('site', 'global', 'sitedisplayname')
        site_url = get_setting('site', 'global', 'siteurl')
        self_reg8n = get_setting('module', 'users', 'selfregistration')

        payment_attempts = self.invoice.payment_set.count()

        # only send email on success! or first fail
        if payment.is_paid or payment_attempts <= 1:
            notification.send_emails(
                [self.registrant.email],  # recipient(s)
                'event_registration_confirmation',  # template
                {
                    'site_label': site_label,
                    'site_url': site_url,
                    'self_reg8n': self_reg8n,
                    'reg8n': self,
                    'event': self.event,
                    'price': self.invoice.total,
                    'is_paid': payment.is_paid,
                },
                True,  # notice saved in db
            )

    @property
    def canceled(self):
        """
        Return True if all registrants are canceled. Otherwise False.
        """
        registrants = self.registrant_set.all()
        for registrant in registrants:
            if not registrant.cancel_dt:
                return False
        return True

    def status(self):
        """
        Returns registration status.
        """
        config = self.event.registration_configuration

        balance = self.invoice.balance
        payment_required = config.payment_required

        if self.canceled:
            return 'cancelled'

        if balance > 0:
            if payment_required:
                return 'payment-required'
            else:
                return 'registered-with-balance'
        else:
            return 'registered'

    @property
    def registrant(self):
        """
        Gets primary registrant.
        Get first registrant w/ email address
        Order by insertion (primary key)
        """

        try:
            registrant = self.registrant_set.filter(
                email__isnull=False).order_by("pk")[0]
        except:
            registrant = None

        return registrant

    def save(self, *args, **kwargs):
        if not self.pk:
            self.guid = str(uuid.uuid1())
        super(Registration, self).save(*args, **kwargs)

    def save_invoice(self, *args, **kwargs):
        status_detail = kwargs.get('status_detail', 'tendered')
        admin_notes = kwargs.get('admin_notes', None)
        
        object_type = ContentType.objects.get(app_label=self._meta.app_label, 
            model=self._meta.module_name)

        try: # get invoice
            invoice = Invoice.objects.get(
                object_type = object_type,
                object_id = self.pk,
            )
        except ObjectDoesNotExist: # else; create invoice
            # cannot use get_or_create method
            # because too many fields are required
            invoice = Invoice()
            invoice.object_type = object_type
            invoice.object_id = self.pk

        # update invoice with details
        invoice.estimate = True
        invoice.status_detail = status_detail
        invoice.subtotal = self.amount_paid
        invoice.total = self.amount_paid
        invoice.balance = invoice.total
        invoice.tender_date = datetime.now()
        invoice.due_date = datetime.now()
        invoice.ship_date = datetime.now()
        invoice.admin_notes = admin_notes
        invoice.save()

        self.invoice = invoice

        self.save()

        return invoice


class Payment(models.Model):
    """
    Event registration payment
    Extends the registration model
    """
    registration = models.OneToOneField('Registration')


class PaymentMethod(models.Model):
    """
    This will hold available payment methods
    Default payment methods are 'Credit Card, Cash and Check.'
    Pre-populated via fixtures
    Soft Deletes required; For historical purposes.
    """
    label = models.CharField(max_length=50, blank=False)

    def __unicode__(self):
        return self.label


class Sponsor(models.Model):
    """
    Event sponsor
    Event can have multiple sponsors
    Sponsor can contribute to multiple events
    """
    event = models.ManyToManyField('Event')


class Discount(models.Model):
    """
    Event discount
    Event can have multiple discounts
    Discount can only be associated with one event
    """
    event = models.ForeignKey('Event')
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)


class Organizer(models.Model):
    """
    Event organizer
    Event can have multiple organizers
    Organizer can maintain multiple events
    """
    event = models.ManyToManyField('Event', blank=True)
    user = models.OneToOneField(User, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True) # static info.
    description = models.TextField(blank=True) # static info.

    def __unicode__(self):
        return self.name


class Speaker(models.Model):
    """
    Event speaker
    Event can have multiple speakers
    Speaker can attend multiple events
    """
    event = models.ManyToManyField('Event', blank=True)
    user = models.OneToOneField(User, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True) # static info.
    description = models.TextField(blank=True) # static info.

    def __unicode__(self):
        return self.name

    def files(self):
        return File.objects.get_for_model(self)

    def get_photo(self):

        if hasattr(self,'cached_photo'):
            return self.cached_photo

        files = File.objects.get_for_model(self).order_by('-update_dt')
        photos = [f for f in files if f.type() == 'image']

        photo = None
        if photos:
            photo = photos[0]  # most recent
            self.cached_photo = photo

        return photo


class Event(TendenciBaseModel):
    """
    Calendar Event
    """
    guid = models.CharField(max_length=40, editable=False)
    entity = models.ForeignKey(Entity, blank=True, null=True)

    type = models.ForeignKey(Type, blank=True, null=True)

    title = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    all_day = models.BooleanField()
    start_dt = models.DateTimeField(default=datetime.now())
    end_dt = models.DateTimeField(default=datetime.now()+timedelta(hours=2))
    timezone = TimeZoneField(_('Time Zone'))

    place = models.ForeignKey('Place', null=True)
    registration_configuration = models.OneToOneField('RegistrationConfiguration', null=True, editable=False)

    private = models.BooleanField() # hide from lists
    password = models.CharField(max_length=50, blank=True)

    # html-meta tags
    meta = models.OneToOneField(MetaTags, null=True)

    objects = EventManager()

    class Meta:
        permissions = (("view_event","Can view event"),)

    def get_meta(self, name):
        """
        This method is standard across all models that are
        related to the Meta model.  Used to generate dynamic
        methods coupled to this instance.
        """
        return EventMeta().get_meta(self, name)

    def is_registrant(self, user):
        return Registration.objects.filter(
            event=self.event, registrant=user).exists()

    @models.permalink
    def get_absolute_url(self):
        return ("event", [self.pk])

    def save(self, *args, **kwargs):
        if not self.pk:
            self.guid = str(uuid.uuid1())
        super(Event, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

    # this function is to display the event date in a nice way.
    # example format: Thursday, August 12, 2010 8:30 AM - 05:30 PM - GJQ 8/12/2010
    def dt_display(self, format_date='%a, %b %d, %Y', format_time='%I:%M %p'):
        from base.utils import format_datetime_range
        return format_datetime_range(self.start_dt, self.end_dt, format_date, format_time)

    @property
    def is_over(self):
        return self.end_dt <= datetime.now()

    @property
    def money_collected(self):
        """
        Total collected from this event
        """
        total_sum = Registration.objects.filter(event=self).aggregate(
            Sum('invoice__total'),
        )['invoice__total__sum']

        # total_sum is the amount of money received when all is said and done
        return total_sum - self.money_outstanding

    @property
    def money_outstanding(self):
        """
        Outstanding balance for this event
        """
        figures = Registration.objects.filter(event=self).aggregate(
            Sum('invoice__total'),
            Sum('invoice__balance'),
        )
        balance_sum = figures['invoice__balance__sum']
        total_sum = figures['invoice__total__sum']

        return total_sum - balance_sum

    def registrants(self, **kwargs):
        """
        This method can return 3 different values.
        All registrants, registrants with a balance, registrants without a balance.
        This method does not respect permissions.
        """

        registrants = Registrant.objects.filter(registration__event=self, cancel_dt=None)

        if 'with_balance' in kwargs:
            with_balance = kwargs['with_balance']

            if with_balance:
                registrants = registrants.filter(registration__invoice__balance__gt=0)
            else:
                registrants = registrants.filter(registration__invoice__balance__lte=0)

        return registrants
