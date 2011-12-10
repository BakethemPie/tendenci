from datetime import datetime

from django.contrib.auth.models import User

from perms.utils import is_admin, is_member
from site_settings.utils import get_setting

from events.utils import get_event_spots_taken, update_event_spots_taken
from events.models import Event, RegConfPricing, Registration, Registrant
from events.registration.constants import REG_CLOSED, REG_FULL, REG_OPEN

try:
    from notification import models as notification
except:
    notification = None


def reg_status(event, user):
    """
    Determines if a registration is open, closed or full.
    """
    
    # check available spots left
    limit = event.registration_configuration.limit
    spots_taken = 0
    if limit > 0: # 0 is no limit
        spots_taken = get_event_spots_taken(event)
        if spots_taken >= limit:
            return 'FULL'
    
    # check if pricings are still open
    pricings = get_available_pricings(event, user)
    if not pricings:
        return 'CLOSED'
        
    return 'OPEN'

def get_available_pricings(event, user):
    """
    Returns the available pricings of an event for a given user.
    """
    pricings = RegConfPricing.objects.filter(
        reg_conf=event.registration_configuration,
        start_dt__lte=datetime.now(),
        end_dt__gt=datetime.now(),
        status=True,
    )
    
    if is_admin(user):
        # return all if admin is user
        return pricings
    
    if not user.is_authenticated():
        # public pricings only
        pricings = pricings.filter(allow_anonymous=True)
    else:
        exclude_list = []
        # user permitted pricings
        for price in pricings:
            # shown to all
            if price.allow_anonymous:
                continue
            
            # Members allowed
            if price.allow_member and is_member(user):
                continue
            
            # Group members allowed
            if price.group and price.group.is_member(user):
                continue
            
            # user failed all permission checks
            exclude_list.append(price.pk)
        # exclude pricings user failed permission checks with
        pricings = pricings.exclude(pk__in=exclude_list)
    
    # return the QUERYSET
    return pricings
    
def can_use_pricing(event, user, pricing):
    """
    Determine if a user can use a specific pricing of a given event
    """
    pricings = get_available_pricings(event, user)
    return pricings.filter(pk=pricing.pk).exists()

def send_registrant_email(reg8n, self_reg8n):
    """
    Email registrant about his/her registration
    """
    
    site_label = get_setting('site', 'global', 'sitedisplayname')
    site_url = get_setting('site', 'global', 'siteurl')
    
    if reg8n.registrant.email:
        notification.send_emails(
            [reg8n.registrant.email],
            'event_registration_confirmation',
            {   
                'SITE_GLOBAL_SITEDISPLAYNAME': site_label,
                'SITE_GLOBAL_SITEURL': site_url,
                'self_reg8n': self_reg8n,
                'reg8n': reg8n,
                'event': reg8n.event,
                'price': reg8n.amount_paid,
                'is_paid': reg8n.invoice.balance == 0
             },
            True, # save notice in db
        )
        
def create_registrant(form, event, reg8n):
    """
    Create the registrant.
    form is a RegistrantForm where the registrant's data is.
    reg8n is the Registration instance to associate the registrant with.
    """
    price = form.get_price()
    
    # initialize the registrant instance and data
    registrant = Registrant()
    registrant.registration = reg8n
    registrant.amount = price
    registrant.pricing = form.cleaned_data['pricing']
    registrant.first_name = form.cleaned_data.get('first_name', '')
    registrant.last_name = form.cleaned_data.get('last_name', '')
    registrant.email = form.cleaned_data.get('email', '')
    registrant.phone = form.cleaned_data.get('phone', '')
    registrant.company_name = form.cleaned_data.get('company_name', '')
    
    # associate the registrant with a user of the same email
    users = User.objects.filter(email=registrant.email)
    if users:
        registrant.user = users[0]
        try:
            user_profile = registrant.user.get_profile()
        except:
             user_profile = None
        if user_profile:
            registrant.mail_name = user_profile.display_name
            registrant.address = user_profile.address
            registrant.city = user_profile.city
            registrant.state = user_profile.state
            registrant.zip = user_profile.zipcode
            registrant.country = user_profile.country
            registrant.company_name = user_profile.company
            registrant.position_title = user_profile.position_title
            
    registrant.save()
    
    return registrant
    
def process_registration(reg_form, reg_formset):
    """
    Create the registrants and the invoice for payment.
    reg_form and reg_formset MUST be validated first
    """
    # init variables
    user = reg_form.get_user()
    event = reg_form.get_event()
    total_price = reg_formset.get_total_price()
    admin_notes = ''
    
    # get the discount, apply if available
    discount = reg_form.cleaned_data['discount']
    if discount:
        total_price = total_price - discount.value
        if total_price < 0:
            total_price = 0
        admin_notes = "%sDiscount code: %s has been enabled for this registration." % (admin_notes, discount.discount_code)
        
    # override event_price to price specified by admin
    if is_admin(user) and total_price > 0:
        admin_price = reg_form.cleaned_data['amount_for_admin']
        if admin_price and admin_price != total_price:
            total_price = admin_price
            admin_notes = "Price has been overriden for this registration."
    
    # create registration
    reg8n_attrs = {
        "event": event,
        "payment_method": reg_form.cleaned_data['payment_method'],
        "amount_paid": total_price,
        "creator": user,
        "owner": user,
    }
    reg8n = Registration.objects.create(**reg8n_attrs)
    
    # create each registrant
    for form in reg_formset.forms:
        registrant_args = [
            form,
            event,
            reg8n,
        ]
        registrant = create_registrant(*registrant_args)
    
    # create invoice
    invoice = reg8n.save_invoice(admin_notes=admin_notes)
    
    # create discount uses for this event, if one was used
    if discount:
        for i in range(0, reg_formset.total_form_count()):
            DiscountUse.objects.create(
                discount=discount,
                invoice=invoice,
            )
    
    # update the spots taken on this event
    update_event_spots_taken(event)
    
    return reg8n
