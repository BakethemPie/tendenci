import re
from django.core.urlresolvers import reverse
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from datetime import datetime
from decimal import Decimal

from profiles.models import Profile
from site_settings.utils import get_setting
from events.models import Registration
from events.models import Registrant, RegConfPricing
from user_groups.models import Group
from perms.utils import is_member, is_admin


def get_vevents(request, d):
    from django.conf import settings
    from timezones.utils import adjust_datetime_to_timezone
    from events.models import Event
    
    site_url = get_setting('site', 'global', 'siteurl')
    
    e_str = ""
    events = Event.objects.search(None, user=request.user)
    for evnt in events:
        event = evnt.object
        e_str += "BEGIN:VEVENT\n"
        
        # organizer
        organizers = event.organizer_set.all()
        if organizers:
            organizer_name_list = [organizer.name for organizer in organizers]
            e_str += "ORGANIZER:%s\n" % (', '.join(organizer_name_list))
        
        # date time 
        if event.start_dt:
            start_dt = adjust_datetime_to_timezone(event.start_dt, settings.TIME_ZONE, 'GMT')
            start_dt = start_dt.strftime('%Y%m%dT%H%M%SZ')
            e_str += "DTSTART:%s\n" % (start_dt)
        if event.end_dt:
            end_dt = adjust_datetime_to_timezone(event.end_dt, settings.TIME_ZONE, 'GMT')
            end_dt = end_dt.strftime('%Y%m%dT%H%M%SZ')
            e_str += "DTEND:%s\n" % (end_dt)
        
        # location
        if event.place:
            e_str += "LOCATION:%s\n" % (event.place.name)
            
        e_str += "TRANSP:OPAQUE\n"
        e_str += "SEQUENCE:0\n"
        
        # uid
        e_str += "UID:uid%d@%s\n" % (event.pk, d['domain_name'])
        
        event_url = "%s%s" % (site_url, reverse('event', args=[event.pk]))
        d['event_url'] = event_url
        
        # text description
        e_str += "DESCRIPTION:%s\n" % (build_ical_text(event,d))
        #  html description
        e_str += "X-ALT-DESC;FMTTYPE=text/html:%s\n" % (build_ical_html(event,d))
        
        e_str += "SUMMARY:%s\n" % strip_tags(event.title)
        e_str += "PRIORITY:5\n"
        e_str += "CLASS:PUBLIC\n"
        e_str += "BEGIN:VALARM\n"
        e_str += "TRIGGER:-PT30M\n"
        e_str += "ACTION:DISPLAY\n"
        e_str += "DESCRIPTION:Reminder\n"
        e_str += "END:VALARM\n"
        e_str += "END:VEVENT\n"
        
    return e_str


def build_ical_text(event, d):
    ical_text = "--- This iCal file does *NOT* confirm registration.\n"
    ical_text += "Event details subject to change. ---\n"
    ical_text += '%s\n\n' % d['event_url']
    
    # title
    ical_text += "Event Title: %s\n" % strip_tags(event.title)
    
    # start_dt
    ical_text += 'Start Date / Time: %s %s\n' % (event.start_dt.strftime('%b %d, %Y %H:%M %p'), event.timezone)
    
    # location
    ical_text += 'Location: %s\n' % (event.place.name)
    
#    # sponsor
#    sponsors = event.sponsor_set.all()
#    if sponsors:
#        sponsor_name_list = [sponsor.name for sponsor in sponsors]
#        ical_text += 'Sponsor: %s\n' % (', '.join(sponsor_name_list))
    
    # speaker
    speakers = event.speaker_set.all()
    if speakers:
        speaker_name_list = [speaker.name for speaker in speakers]
        ical_text += 'Speaker: %s\n' % (', '.join(speaker_name_list))
        
    # maps
    show_map_link = False
    if (event.place.address and event.place.city and event.place.state) \
                or (event.place.address and event.place.zip):
        show_map_link = True
    if show_map_link:
        ical_text += "Google\n"
        ical_text += "http://maps.google.com/maps?q="
        ical_text += event.place.address.replace(" ", "+")
        if event.place.city:
            ical_text += ','
            ical_text += event.place.city
        if event.place.state:
            ical_text += ','
            ical_text += event.place.state
        if event.place.zip:
            ical_text += ','
            ical_text += event.place.zip
            
        ical_text += "\n\nForecast\n"
        ical_text += "http://www.weather.com/weather/monthly/%s\n\n" % (event.place.zip)
            
    ical_text += strip_tags(event.description)
    
    ical_text += "--- This iCal file does *NOT* confirm registration."
    ical_text += "Event details subject to change. ---\n\n"
    ical_text += "--- Tendenci(tm) Software by Schipul.com - The Web Marketing Company ---\n"
    
    ical_text  = ical_text.replace(';', '\;')
    ical_text  = ical_text.replace('\n', '\\n')
   
    return ical_text


def build_ical_html(event, d):
    # disclaimer: registration
    ical_html = "<div>--- This iCal file does *NOT* confirm registration."
    ical_html += "Event details subject to change. ---</div>"
    
    # title
    ical_html += "<h1>Event Title: %s</h1>" % (event.title)
    
    ical_html += '<div>%s</div><br />' % d['event_url']
    
    # start_dt
    ical_html += '<div>When: %s %s</div>' % (event.start_dt.strftime('%b %d, %Y %H:%M %p'), event.timezone)
    
#    # sponsor
#    sponsors = event.sponsor_set.all()
#    if sponsors:
#        sponsor_name_list = [sponsor.name for sponsor in sponsors]
#        ical_html += '<div>Sponsor: %s</div>' % (', '.join(sponsor_name_list))
    
    # speaker
    speakers = event.speaker_set.all()
    if speakers:
        speaker_name_list = [speaker.name for speaker in speakers]
        ical_html += '<div>Speaker: %s</div>' % (', '.join(speaker_name_list))
        
    ical_html += '<br />'
    
    # maps
    show_map_link = False
    if (event.place.address and event.place.city and event.place.state) \
                or (event.place.address and event.place.zip):
        show_map_link = True
    if show_map_link:
        # location
        ical_html += '%s<br />' % (event.place.name)
        ical_html += '%s<br />' % (event.place.address)
        if event.place.city and event.place.state:
            ical_html += '%s, %s' % (event.place.city, event.place.state)
        if event.place.zip:
            ical_html += ' %s' % (event.place.zip)
        ical_html += '<br />'
    
        ical_html += "<div>"
        ical_html += "http://maps.google.com/maps?q="
        ical_html += event.place.address.replace(" ", "+")
        if event.place.city:
            ical_html += ','
            ical_html += event.place.city
        if event.place.state:
            ical_html += ','
            ical_html += event.place.state
        if event.place.zip:
            ical_html += ','
            ical_html += event.place.zip
        ical_html += "</div><br />"
            
        ical_html += "<div>Forecast: "
        ical_html += "http://www.weather.com/weather/monthly/%s</div><br /><br />" % (event.place.zip)
            
    ical_html += '<div>%s</div>' % (event.description)
    
    ical_html += "<div>--- This iCal file does *NOT* confirm registration."
    ical_html += "Event details subject to change. ---</div>"
    ical_html += "<div>--- Tendenci&reg; Software by <a href=\"http://www.schipul.com\">schipul.com</a>"
    ical_html += " - The Web Marketing Company ---</div>"
    
    ical_html  = ical_html.replace(';', '\;')
    #ical_html  = degrade_tags(ical_html.replace(';', '\;'))
   
    return ical_html


def degrade_tags(str):
    # degrade header tags h1, h2..., h6 to font tags for MS outlook
    # h1 --> font size 6
    str = re.sub(r'<h1[^>]*>(.*?)</h1>', r'<div><strong><font size="6">\1</font></strong></div>', str)
    
    # h2 --> font size 5
    str = re.sub(r'<h2[^>]*>(.*?)</h2>', r'<div><strong><font size="5">\1</font></strong></div>', str)
    
    # h3 --> font size 4
    str = re.sub(r'<h3[^>]*>(.*?)</h3>', r'<div><strong><font size="4">\1</font></strong></div>', str)
    
    # h4 --> font size 3
    str = re.sub(r'<h4[^>]*>(.*?)</h4>', r'<div><strong><font size="3">\1</font></strong></div>', str)
    
    # h5 --> font size 2
    str = re.sub(r'<h5[^>]*>(.*?)</h5>', r'<div><strong><font size="2">\1</font></strong></div>', str)
    
    # h6 --> font size 1
    str = re.sub(r'<h6[^>]*>(.*?)</h6>', r'<div><strong><font size="1">\1</font></strong></div>', str)
    
    return str
      

def next_month(month, year):
    # TODO: cleaner way to get next date
    next_month = (month+1)%13
    next_year = year
    if next_month == 0:
        next_month = 1
        next_year += 1

    return (next_month, next_year)


def prev_month(month, year):
    # TODO: cleaner way to get previous date
    prev_month = (month-1)%13
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    return (prev_month, prev_year)


def email_registrants(event, email, **kwargs):

    reg8ns = Registration.objects.filter(event=event)

    payment_status = kwargs.get('payment_status', 'all')


    if payment_status == 'all':
        registrants = event.registrants()
    elif payment_status == 'paid':
        registrants = event.registrants(with_balance=False)
    elif payment_status == 'not-paid':
        registrants = event.registrants(with_balance=True)
    else:
        raise Exception(
            'Acceptable payment_status field value not found'
        )

    # i had these two lines initially to temporarily hold the original email body
    # please DO NOT remove them. Otherwise, all recipients would have the same names.
    # as the first registrant in the email body. - GJQ  4/13/2011
    tmp_body = email.body
        
    for registrant in registrants:
        first_name = registrant.first_name
        last_name = registrant.last_name

        email.recipient = registrant.email
        
        email.body = email.body.replace('[firstname]', first_name)
        email.body = email.body.replace('[lastname]', last_name)
        email.send()
        
        email.body = tmp_body  # restore to the original


def save_registration(*args, **kwargs):
    """
    Adds or Updates the Registration Record.
    Updates Registration, Registrant, and Invoice Table.
    """

    user = kwargs.get('user', None)
    event = kwargs.get('event', None)
    payment_method = kwargs.get('payment_method')
    price = kwargs.get('price', None)

    if not isinstance(user, User):
        user = None
        
    registrant_set_defaults = {
        'user': user,
        'name': '',
        'first_name': kwargs.get('first_name', ''),
        'last_name': kwargs.get('last_name', ''),
        'email': kwargs.get('email', ''),
        'mail_name': '',
        'address': '',
        'city': '',
        'state': '',
        'zip': '',
        'country': '',
        'phone': kwargs.get('phone', ''),
        'company_name': kwargs.get('company_name', ''),
        'position_title': '',
        'amount': price
    }

    # standardize user_account & user_profile
    # consider authenticated and anonymous
    if user:
        user_profile = user.get_profile()

        registrant_set_defaults.update({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'mail_name': user_profile.display_name,
            'address': user_profile.address,
            'city': user_profile.city,
            'state': user_profile.state,
            'zip': user_profile.zipcode,
            'country': user_profile.country,
            'phone': user_profile.phone,
            'company_name': user_profile.company,
            'position_title': user_profile.position_title,
        })

    # if no name; use email address
    # if not user_profile.display_name:
    # user_profile.display_name = user_profile.email
    try:
        # find registrant using event + email
        registrant = Registrant.objects.get(
            registration__event=event, 
            email=registrant_set_defaults['email'],
            cancel_dt=None,
        )
        reg8n = registrant.registration
        created = False
    except: # create registration; then registrant
        reg8n_attrs = {
            "event": event,
            "payment_method": payment_method,
            "amount_paid": str(price),
        }

        # volatile fields
        if user:
            reg8n_attrs["creator"] = user
            reg8n_attrs["owner"] = user

        # create registration
        reg8n = Registration.objects.create(**reg8n_attrs)

        # create registrant
        registrant = reg8n.registrant_set.create(**registrant_set_defaults)
        
        created = True

    reg8n.save_invoice()
    return (reg8n, created)


def add_registration(*args, **kwargs):
    """
    Add the registration
    Args are split up below into the appropriate attributes
    """
    from decimal import Decimal
    total_amount = 0
    count = 0

    # arguments were getting kinda long
    # moved them to an unpacked version
    request, event, reg_form, \
    registrant_formset, price, \
    event_price = args
    
    event_price = Decimal(str(event_price))
    
    #kwargs
    admin_notes = kwargs.get('admin_notes', None)

    reg8n_attrs = {
        "event": event,
        "payment_method": reg_form.cleaned_data.get('payment_method'),
        "amount_paid": str(total_amount),
        "reg_conf_price": price
    }
    if request.user.is_authenticated():
        reg8n_attrs['creator'] = request.user
        reg8n_attrs['owner'] = request.user
        
    # create registration
    reg8n = Registration.objects.create(**reg8n_attrs)
    
    for form in registrant_formset.forms:
        amount = event_price
        if not count % price.quantity == 0:
            amount = Decimal('0.00')
        if not form in registrant_formset.deleted_forms:
            registrant_args = [
                form,
                event,
                reg8n,
                price,
                amount
            ]
            registrant = create_registrant_from_form(*registrant_args)
            total_amount += registrant.amount 
            
            count += 1
    
    # update reg8n with the real amount
    reg8n.amount_paid = total_amount
    
    created = True
    
    # create invoice
    reg8n.save_invoice(admin_notes=admin_notes)
    return (reg8n, created)


def create_registrant_from_form(*args, **kwargs):
    """
    Create the registrant
    Args are split up below into the appropriate attributes
    """
    # arguments were getting kinda long
    # moved them to an unpacked version
    form, event, reg8n, \
    price, amount = args

    registrant = Registrant()
    registrant.registration = reg8n
    registrant.amount = amount

    registrant.first_name = form.cleaned_data.get('first_name', '')
    registrant.last_name = form.cleaned_data.get('last_name', '')
    registrant.email = form.cleaned_data.get('email', '')
    registrant.phone = form.cleaned_data.get('phone', '')
    registrant.company_name = form.cleaned_data.get('company_name', '')

    
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


def gen_pricing_dict(price, qualifies, failure_type, admin=False):
    """
    Generates a pricing dict based on the current date.
    Disregards time if admin is set to True.
    """
    now = datetime.now()
    if admin:
        pricing = {
            'price': price,
            'amount': price.price,
            'qualifies': qualifies,
            'failure_type': failure_type,
        }
    else:
        if now >= price.start_dt and now <= price.end_dt:
            pricing = {
                'price': price,
                'amount': price.price,
                'qualifies': qualifies,
                'failure_type': failure_type,
            }
        else:
            pricing = {}
    return pricing


def get_pricing(user, event, pricing=None):
    """
    Get a list of qualified pricing in a dictionary
    form with keys as helpers:

    qualified: boolean that tells you if they qualify
               to use this price

    price: instance of the RegConfPricing model

    type: string that holds what price type (early,
          regular or late)

    failure_type: string of what permissions it failed on
    """
    pricing_list = []
    limit = event.registration_configuration.limit
    spots_taken = get_event_spots_taken(event)
    spots_left = limit - spots_taken
    if not pricing:
        pricing = RegConfPricing.objects.filter(
            reg_conf=event.registration_configuration
        )
        
    print pricing

    # iterate and create a dictionary based
    # on dates and permissions
    # gen_pricing_dict(price_instance, qualifies)
    for price in pricing:
        qualifies = True
        
        # Admins are always true
        # This should always be at the top of this code
        if is_admin(user):
            qualifies = True
            pricing_list.append(gen_pricing_dict(
               price, 
               qualifies, 
               '',
               admin=True)
            )
            continue

        # limits
        if limit > 0:
            if spots_left < price.quantity:
              qualifies = False
              pricing_list.append(gen_pricing_dict(
                price, 
                qualifies, 
                'limit')
              )
              continue

        # public pricing is always true
        if price.allow_anonymous:
            qualifies = True
            pricing_list.append(gen_pricing_dict(
               price,
               qualifies, 
               '')
            )
            continue

        # Admin only price
        if not any([price.allow_user, price.allow_anonymous, price.allow_member, price.group]):
            if not is_admin(user):
                continue      

        # User permissions
        if price.allow_user and not user.is_authenticated():
            qualifies = False
            pricing_list.append(gen_pricing_dict(
               price, 
               qualifies, 
               'user')
            )
            continue

        # Group and Member permissions
        if price.group and price.allow_member:
            qualifies = False
            
            if price.group.is_member(user) or is_member(user):
                qualifies = True            
                pricing_list.append(gen_pricing_dict(
                   price, 
                   qualifies, 
                   '')
                )
                continue

        # Group permissions
        if price.group and not price.group.is_member(user):
            qualifies = False
            pricing_list.append(gen_pricing_dict(
               price, 
               qualifies, 
               'group')
            )
            continue

        # Member permissions
        if price.allow_member and not is_member(user):
            qualifies = False
            pricing_list.append(gen_pricing_dict(
               price, 
               qualifies, 
               'member')
            )
            continue

        # pricing is true if doesn't get stopped above
        pricing_list.append(gen_pricing_dict(
           price, 
           qualifies, 
           '')
        )

    # pop out the empty ones if they exist
    pricing_list = [i for i in pricing_list if i]

    # sort the pricing from smallest to largest
    # by price
    sorted_pricing_list = []
    if pricing_list:
        sorted_pricing_list = sorted(
            pricing_list, 
            key=lambda k: k['amount']
        )

        # set a default pricing on the first
        # one that qualifies
        for price in sorted_pricing_list:
            if price['qualifies']:
                price.update({
                    'default': True,
                })
                break
    
    print sorted_pricing_list
    return sorted_pricing_list


def count_event_spots_taken(event):
    """
    Count the number of spots taken in an event
    """
    registrations = Registration.objects.filter(event=event)
    count = 0

    for reg in registrations:
        count += reg.registrant_set.count()
    
    return count


def update_event_spots_taken(event):
    """
    Update the index registration count for 
    an event
    """
    from events.search_indexes import EventIndex
    from events.models import Event

    event_index = EventIndex(Event)
    event.spots_taken = count_event_spots_taken(event)
    event_index.update_object(event)

    return event.spots_taken


def get_event_spots_taken(event):
    """
    Get the index registration count for
    an event
    """
    from haystack.query import SearchQuerySet
    from events.models import Event
    sqs = SearchQuerySet().models(Event)
    sqs = sqs.filter(primary_key=event.pk)

    try:
        spots_taken = sqs[0].spots_taken
        if not spots_taken:
            spots_taken = update_event_spots_taken(event)
        return spots_taken
    except IndexError:
        return update_event_spots_taken(event)
    return 0


def registration_earliest_time(event, pricing=None):
    """
    Get the earlist time out of all the pricing.
    This will not consider any registrations that have ended.
    """
    
    if not pricing:
        pricing = RegConfPricing.objects.filter(
            reg_conf=event.registration_configuration,
        )
    
    pricing = pricing.filter(end_dt__gt=datetime.now()).order_by('start_dt')
    
    try:
        return pricing[0].start_dt
    except IndexError:
        return None

def registration_has_started(event, pricing=None):
    """
    Check all times and make sure the registration has
    started
    """
    reg_started = []
    
    if not pricing:
        pricing = RegConfPricing.objects.filter(
            reg_conf=event.registration_configuration
        )
    
    for price in pricing:
        reg_started.append(
            price.registration_has_started
        )
    
    return any(reg_started)
    
def registration_has_ended(event, pricing=None):
    """
    Check all times and make sure the registration has
    ended
    """
    reg_ended = []
    
    if not pricing:
        pricing = RegConfPricing.objects.filter(
            reg_conf=event.registration_configuration
        )
    
    for price in pricing:
        reg_ended.append(
            price.registration_has_ended
        )
    
    return all(reg_ended)

def clean_price(price, user):
    """
    Used to validate request.POST.price in the multi-register view.
    amount is not validated if user is admin.
    """
    price_pk, amount = price.split('-')
    price = RegConfPricing.objects.get(pk=price_pk)
    amount = Decimal(str(amount))
    
    if amount != price.price and not is_admin(user):
        raise ValueError("Invalid price amount")
    
    return price, price_pk, amount
