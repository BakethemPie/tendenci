import hashlib
from datetime import datetime

from django.contrib.humanize.templatetags.humanize import naturalday
from django.core.urlresolvers import reverse
from django.template.defaultfilters import floatformat
from django.db import models
from django.template import Node, Library, TemplateSyntaxError, Variable
from django.contrib.auth.models import AnonymousUser

from events.models import Event, Registrant, Type
from base.template_tags import ListNode, parse_tag_kwargs

register = Library()


@register.inclusion_tag("events/options.html", takes_context=True)
def event_options(context, user, event):
    context.update({
        "opt_object": event,
        "user": user
    })
    return context


@register.inclusion_tag("events/nav.html", takes_context=True)
def event_nav(context, user, event=None):
    context.update({
        "nav_object": event,
        "user": user,
        "today": datetime.today()
    })
    return context


@register.inclusion_tag("events/search-form.html", takes_context=True)
def event_search(context):
    return context


@register.inclusion_tag("events/registrants/options.html", takes_context=True)
def registrant_options(context, user, registrant):
    context.update({
        "opt_object": registrant,
        "user": user
    })
    return context


@register.inclusion_tag("events/registrants/search-form.html", takes_context=True)
def registrant_search(context, event=None):

    context.update({
        "event": event
    })

    return context

@register.inclusion_tag("events/registrants/roster_registrants.html")
def roster_display_registrants(registrants_search_list, registration):
    # given a list of registrants, display them if they belong to this registration
    # the purpose of this template is to reduce the db access. so we don't need to 
    # call registration.registrant_set.
    registrants = []
    for registrant in registrants_search_list:
        registrant = registrant.object
        if registrant.registration.pk == registration.pk:
            registrants.append(registrant)
    registrants.sort(cmp=cmp_registrants)
    
    return {'registrants': registrants}

def cmp_registrants(r1, r2):
    # sort by id in ascending order
    if r1.id > r2.id: return 1
    if r1.id == r2.id: return 0
    if r1.id < r2.id: return -1


@register.inclusion_tag('events/reg8n/register-button.html', takes_context=True)
def register_button(context):
    event = context['event']
    user = context['user']
    reg8n_config = event.registration_configuration

    # Set the variables ------------------

    reg8n_enabled = reg8n_config and reg8n_config.enabled

    if reg8n_enabled:
        reg8n_price = reg8n_config.price or float(0)

    if user.is_anonymous():
        registrant = None
    else:
        try:
            registrant = Registrant.objects.get(
                registration__event=event,
                email= ser.email,
                cancel_dt=None,
            )
        except:
            registrant = None

    registrants = Registrant.objects.filter(registration__event=event)
    if reg8n_config.payment_required:
        registrants = registrants.filter(registration__invoice__balance__lte=0)

    infinite_limit = reg8n_config.limit <= 0
    reg8n_full = (registrants.count() >= reg8n_config.limit) and not infinite_limit

    url1, msg1, msg2, status_class = '', '', '', ''

    if reg8n_enabled:
        if reg8n_config.within_time:

            msg2 = 'Registration ends %s' % naturalday(reg8n_config.late_dt)
            status_class = 'open'
            url1 = reverse('event.register', args=[event.pk])

            if registrant:
                msg1 = 'You are registered'
                status_class = 'registered'
                url1 = registrant.hash_url()
            else:

                if reg8n_price:
                    msg1 = '$%s to Register' % floatformat(reg8n_price)
                else:
                    msg1 = 'Register for Free'

                if reg8n_full:
                    msg1 = 'Registration Full'
                    status_class = 'closed'
                    url1 = ''
        else:

            if reg8n_config.early_dt > datetime.now():
                msg2 = 'Registration opens %s' % naturalday(reg8n_config.early_dt)
            else:
                msg2 = 'Registration ended %s' % naturalday(reg8n_config.late_dt)

            status_class = 'closed'

            if registrant:
                msg1 = 'You are registered'
                status_class = 'registered'
                url1 = registrant.hash_url()
            else:
                msg1 = 'Registration Closed'

    return {
        'reg8n_enabled': reg8n_enabled,
        'url1': url1,
        'msg1': msg1,
        'msg2': msg2,
        'status_class': status_class
    }


class EventListNode(Node):
    def __init__(self, day, type_slug, context_var):

        self.day = Variable(day)
        self.type_slug = Variable(type_slug)
        self.context_var = context_var

    def render(self, context):

        day = self.day.resolve(context)
        type_slug = self.type_slug.resolve(context)
        type = None

        filters = [
            'start_day:%s' % day.day,
            'start_month:%s' % day.month,
            'start_year:%s' % day.year,
        ]

        type_sqs = Type.objects.search()
        type_sqs = type_sqs.filter(slug=type_slug)

        if type_sqs and type_sqs[0]:
            type = type_sqs[0].object

        if type:
            filters.append('type_id:%s' % type.pk)

        sqs = Event.objects.search_filter(
            filters=filters,
            user=context['user']).order_by('start_dt')
        events = [sq.object for sq in sqs]

        context[self.context_var] = events
        return ''


@register.tag
def event_list(parser, token):
    """
    Example: {% event_list day as events %}
             {% event_list day type as events %}
    """
    bits = token.split_contents()
    type_slug = None

    if len(bits) != 4 and len(bits) != 5:
        message = '%s tag requires 4 or 5 arguments' % bits[0]
        raise TemplateSyntaxError(message)

    if len(bits) == 4:
        day = bits[1]
        context_var = bits[3]

    if len(bits) == 5:
        day = bits[1]
        type_slug = bits[2]
        context_var = bits[4]

    return EventListNode(day, type_slug, context_var)


class IsRegisteredUserNode(Node):

    def __init__(self, user, event, context_var):
        self.user = Variable(user)
        self.event = Variable(event)
        self.context_var = context_var

    def render(self, context):

        user = self.user.resolve(context)
        event = self.event.resolve(context)

        if isinstance(user, AnonymousUser):
            exists = False
        else:
            exists = Registrant.objects.filter(
                registration__event=event,
                email=user.email,
                cancel_dt=None,
            ).exists()

        context[self.context_var] = exists
        return ''


@register.tag
def is_registered_user(parser, token):
    """
    Example: {% is_registered_user user event as registered_user %}
    """
    bits = token.split_contents()

    if len(bits) != 5:
        message = '%s tag requires 5 arguments' % bits[0]
        raise TemplateSyntaxError(message)

    user = bits[1]
    event = bits[2]
    context_var = bits[4]

    return IsRegisteredUserNode(user, event, context_var)


class ListEventsNode(ListNode):
    model = Event
    
    def __init__(self, context_var, *args, **kwargs):
        self.context_var = context_var
        self.kwargs = kwargs

        if not self.model:
            raise AttributeError(_('Model attribute must be set'))
        if not issubclass(self.model, models.Model):
            raise AttributeError(_('Model attribute must derive from Model'))
        if not hasattr(self.model.objects, 'search'):
            raise AttributeError(_('Model.objects does not have a search method'))

    def render(self, context):
        tags = u''
        query = u''
        user = AnonymousUser()
        limit = 3
        order = u''
        randomize = False

        if 'random' in self.kwargs:
            randomize = bool(self.kwargs['random'])

        if 'tags' in self.kwargs:
            try:
                tags = Variable(self.kwargs['tags'])
                tags = unicode(tags.resolve(context))
            except:
                tags = self.kwargs['tags']

            tags = tags.replace('"', '')
            tags = tags.split(',')
            
            print tags

        if 'user' in self.kwargs:
            try:
                user = Variable(self.kwargs['user'])
                user = user.resolve(context)
            except:
                user = self.kwargs['user']
        else:
            # check the context for an already existing user
            if 'user' in context:
                user = context['user']

        if 'limit' in self.kwargs:
            try:
                limit = Variable(self.kwargs['limit'])
                limit = limit.resolve(context)
            except:
                limit = self.kwargs['limit']

        limit = int(limit)

        if 'query' in self.kwargs:
            try:
                query = Variable(self.kwargs['query'])
                query = query.resolve(context)
            except:
                query = self.kwargs['query']  # context string

        if 'order' in self.kwargs:
            try:
                order = Variable(self.kwargs['order'])
                order = order.resolve(context)
            except:
                order = self.kwargs['order']

        # process tags
        for tag in tags:
            tag = tag.strip()
            query = '%s "tag:%s"' % (query, tag)

        # get the list of staff
        items = self.model.objects.search(user=user, query=query)

        # if order is not specified it sorts by relevance
        if order:
            if order == "next_upcoming":
                items = items.filter(start_dt__gt = datetime.now())
                items = items.order_by("start_dt")
            else:
                items = items.order_by(order)

        if randomize:
            objects = [item.object for item in random.sample(items, items.count())][:limit]
        else:
            objects = [item.object for item in items[:limit]]

        context[self.context_var] = objects
        return ""


@register.tag
def list_events(parser, token):
    """
    Example:
        {% list_events as events [user=user limit=3] %}
        {% for event in events %}
            {{ event.title }}
        {% endfor %}

    """
    args, kwargs = [], {}
    bits = token.split_contents()
    context_var = bits[2]

    if len(bits) < 3:
        message = "'%s' tag requires more than 3" % bits[0]
        raise TemplateSyntaxError(message)

    if bits[1] != "as":
        message = "'%s' second argument must be 'as" % bits[0]
        raise TemplateSyntaxError(message)

    kwargs = parse_tag_kwargs(bits)

    if 'order' not in kwargs:
        kwargs['order'] = '-start_dt'

    return ListEventsNode(context_var, *args, **kwargs)
