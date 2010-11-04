import re

from django.template import Library
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

register = Library()

@register.filter(name="localize_date")
def localize_date(value, to_tz=None):
    from timezones.utils import adjust_datetime_to_timezone
    try:
        if to_tz is None:
            to_tz=settings.UI_TIME_ZONE
            
        from_tz=settings.TIME_ZONE
        
        return adjust_datetime_to_timezone(value,from_tz=from_tz,to_tz=to_tz)
    except AttributeError:
        return ''

localize_date.is_safe = True

@register.filter_function
def date_short(value, arg=None):
    """Formats a date according to the given format."""
    from django.utils.dateformat import format
    from site_settings.utils import get_setting
    if not value:
        return u''
    if arg is None:
        s_date_format = get_setting('site','global','dateformat')
        if s_date_format:
            arg = s_date_format
        else:
            arg = settings.SHORT_DATETIME_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''
date_short.is_safe = False

@register.filter_function
def date_long(value, arg=None):
    """Formats a date according to the given format."""
    from django.utils.dateformat import format
    from site_settings.utils import get_setting
    if not value:
        return u''
    if arg is None:
        s_date_format = get_setting('site','global','dateformatlong')
        if s_date_format:
            arg = s_date_format
        else:
            arg = settings.DATETIME_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''
date_long.is_safe = False

@register.filter_function
def date(value, arg=None):
    """Formats a date according to the given format."""
    from django.utils.dateformat import format
    if not value:
        return u''
    if arg is None:
        arg = settings.DATETIME_FORMAT
    else:
        if arg == 'long':
            return date_long(value)
        if arg == 'short':
            return date_short(value)
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''
date_long.is_safe = False

@register.filter_function
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)

@register.filter_function
def in_group(user, group):
    if group:
        return group in [dict['pk'] for dict in user.group_set.values('pk')]
    else:
        return False

@register.filter
def domain(link):
    from urlparse import urlparse
    link = urlparse(link)
    return link.hostname

@register.filter
def strip_template_tags(string):
    import re
    p = re.compile('{[#{%][^#}%]+[%}#]}')
    return re.sub(p,'',string)
    
@register.filter
@stringfilter      
def stripentities(value):
    """Strips all [X]HTML tags."""
    from django.utils.html import strip_entities
    return strip_entities(value)
stripentities.is_safe = True

@register.filter     
def format_currency(value):
    """format currency"""
    from base.utils import tcurrency
    return tcurrency(value)
format_currency.is_safe = True

@register.filter
def scope(object):
    return dir(object)

@register.filter
@stringfilter
def basename(path):
    from os.path import basename
    return basename(path)

@register.filter     
def date_diff(value, date_to_compare=None):
    """Compare two dates and return the difference in days"""
    import datetime
    if not isinstance(value, datetime.datetime):
        return 0
    
    if not isinstance(date_to_compare, datetime.datetime):
        date_to_compare = datetime.datetime.now()
    
    return (date_to_compare-value).days

@register.filter
def first_chars(string, arg):
    """ returns the first x characters from a string """
    string = str(string)
    if arg:
        if not arg.isdigit(): return string
        return string[:int(arg)]
    else:
        return string
    return string

@register.filter
def rss_date(value, arg=None):
    """Formats a date according to the given format."""
    from django.utils import formats
    from django.utils.dateformat import format
    from datetime import datetime

    if not value:
        return u''
    else:
        value = datetime(*value[:-3])
    if arg is None:
        arg = settings.DATE_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''
rss_date.is_safe = False

@register.filter()
def obfuscate_email(email, linktext=None, autoescape=None):
    """
    Given a string representing an email address,
    returns a mailto link with rot13 JavaScript obfuscation.
    
    Accepts an optional argument to use as the link text;
    otherwise uses the email address itself.
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    email = re.sub('@','\\\\100', re.sub('\.', '\\\\056', \
        esc(email))).encode('rot13')

    if linktext:
        linktext = esc(linktext).encode('rot13')
    else:
        linktext = email

    rotten_link = """<script type="text/javascript">document.write \
        ("<n uers=\\\"znvygb:%s\\\">%s<\\057n>".replace(/[a-zA-Z]/g, \
        function(c){return String.fromCharCode((c<="Z"?90:122)>=\
        (c=c.charCodeAt(0)+13)?c:c-26);}));</script>""" % (email, linktext)
    return mark_safe(rotten_link)
obfuscate_email.needs_autoescape = True


    