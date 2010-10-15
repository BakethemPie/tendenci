import re
from django.template import Node, Library, TemplateSyntaxError, Variable, VariableDoesNotExist
from django.core.urlresolvers import reverse
from photos.models import Image, Pool
register = Library()


class PrintExifNode(Node):

    def __init__(self, exif):
        self.exif = exif

    def render(self, context):
        try:
            exif = unicode(self.exif.resolve(context, True))
        except VariableDoesNotExist:
            exif = u''

        EXPR =  "'(?P<key>[^:]*)'\:(?P<value>[^,]*),"
        expr = re.compile(EXPR)
        msg  = "<table>"
        for i in expr.findall(exif):
            msg += "<tr><td>%s</td><td>%s</td></tr>" % (i[0],i[1])

        msg += "</table>"

        return u'<div id="exif">%s</div>' % (msg)


@register.tag(name="print_exif")
def do_print_exif(parser, token):
    try:
        tag_name, exif = token.contents.split()
    except ValueError:
        msg = '%r tag requires a single argument' % token.contents[0]
        raise TemplateSyntaxError(msg)

    exif = parser.compile_filter(exif)
    return PrintExifNode(exif)


class PublicPhotosNode(Node):
    
    def __init__(self, context_var, user_var=None, use_pool=False):
        self.context_var = context_var
        if user_var is not None:
            self.user_var = Variable(user_var)
        else:
            self.user_var = None
        self.use_pool = use_pool
    
    def render(self, context):
        
        use_pool = self.use_pool
        
        if use_pool:
            queryset = Pool.objects.filter(
                photo__is_public = True,
            ).select_related("photo")
        else:
            queryset = Image.objects.filter(is_public=True).order_by('-date_added')
        
        if self.user_var is not None:
            user = self.user_var.resolve(context)
            if use_pool:
                queryset = queryset.filter(photo__member=user)
            else:
                queryset = queryset.filter(member=user)
        
        context[self.context_var] = queryset
        return ""

@register.tag
def public_photos(parser, token, use_pool=False):
    
    bits = token.split_contents()
    
    if len(bits) != 3 and len(bits) != 5:
        message = "'%s' tag requires three or five arguments" % bits[0]
        raise TemplateSyntaxError(message)
    else:
        if len(bits) == 3:
            if bits[1] != 'as':
                message = "'%s' second argument must be 'as'" % bits[0]
                raise TemplateSyntaxError(message)
            
            return PublicPhotosNode(bits[2], use_pool=use_pool)
            
        elif len(bits) == 5:
            if bits[1] != 'for':
                message = "'%s' second argument must be 'for'" % bits[0]
                raise TemplateSyntaxError(message)
            if bits[3] != 'as':
                message = "'%s' forth argument must be 'as'" % bits[0]
                raise TemplateSyntaxError(message)
            
            return PublicPhotosNode(bits[4], bits[2], use_pool=use_pool)

@register.tag
def public_pool_photos(parser, token):
    return public_photos(parser, token, use_pool=True)

@register.inclusion_tag("photos/options.html", takes_context=True)
def photo_options(context, user, photo):
    context.update({
        "opt_object": photo,
        "user": user
    })
    return context

@register.inclusion_tag("photos/nav.html", takes_context=True)
def photo_nav(context, user, photo=None):
    context.update({
        "nav_object": photo,            
        "user": user
    })
    return context

@register.inclusion_tag("photos/photo-set/options.html", takes_context=True)
def photo_set_options(context, user, photo_set):
    context.update({
        "opt_object": photo_set,
        "user": user
    })
    return context

@register.inclusion_tag("photos/photo-set/nav.html", takes_context=True)
def photo_set_nav(context, user, photo_set=None):
    context.update({
        "nav_object": photo_set,
        "user": user
    })
    return context

@register.inclusion_tag("photos/photo-set/search-form.html", takes_context=True)
def photo_set_search(context):
    return context


class ListPhotosNode(Node):
    
    def __init__(self, context_var, *args, **kwargs):

        self.limit = 3
        self.user = None
        self.tags = []
        self.q = []
        self.context_var = context_var

        if "limit" in kwargs:
            self.limit = Variable(kwargs["limit"])
        if "user" in kwargs:
            self.user = Variable(kwargs["user"])
        if "tags" in kwargs:
            self.tags = kwargs["tags"]
        if "q" in kwargs:
            self.q = kwargs["q"]

    def render(self, context):
        query = ''

        if self.user:
            self.user = self.user.resolve(context)

        if hasattr(self.limit, "resolve"):
            self.limit = self.limit.resolve(context)

        for tag in self.tags:
            tag = tag.strip()
            query = '%s "tag:%s"' % (query, tag)

        for q_item in self.q:
            q_item = q_item.strip()
            query = '%s "%s"' % (query, q_item)

        photos = Image.objects.search(user=self.user, query=query)

        photos = [photo.object for photo in photos[:self.limit]]
        context[self.context_var] = photos
        return ""

@register.tag
def list_photos(parser, token):
    """
    Example:
        {% list_photos as photos [user=user limit=3] %}
        {% for photo in photos %}
            {{ photo.title }}
        {% endfor %}

    """
    args, kwargs = [], {}
    bits = token.split_contents()
    context_var = bits[2]

    for bit in bits:
        if "limit=" in bit:
            kwargs["limit"] = bit.split("=")[1]
        if "user=" in bit:
            kwargs["user"] = bit.split("=")[1]
        if "tags=" in bit:
            kwargs["tags"] = bit.split("=")[1].replace('"','').split(',')
        if "q=" in bit:
            kwargs["q"] = bit.split("=")[1].replace('"','').split(',')

    if len(bits) < 3:
        message = "'%s' tag requires more than 3" % bits[0]
        raise TemplateSyntaxError(message)

    if bits[1] != "as":
        message = "'%s' second argument must be 'as" % bits[0]
        raise TemplateSyntaxError(message)

    return ListPhotosNode(context_var, *args, **kwargs)

class PhotoImageURL(Node):
    
    def __init__(self, photo, *args, **kwargs):

        self.size = "100x100"
        self.crop = False

        self.photo = Variable(photo)

        if "size" in kwargs:
            self.size = kwargs["size"]
        if "crop" in kwargs:
            self.crop = kwargs["crop"]

    def render(self, context):
        photo = self.photo.resolve(context)

        if self.crop:
            url = reverse('photo.size', 
                args=[photo.pk, self.size, "crop"])
        else:
            url = reverse('photo.size', 
                args=[photo.pk, self.size])

        return url

@register.tag
def photo_image_url(parser, token):
    """
    Example:
        {% list_photos as photos user=user limit=3 %}
        {% for photo in photos %}
            {% photo_size photo size=100x100 crop=True %}
        {% endfor %}
    """
    args, kwargs = [], {}
    bits = token.split_contents()
    photo = bits[1]

    for bit in bits:
        if "size=" in bit:
            kwargs["size"] = bit.split("=")[1]
        if "crop=" in bit:
            kwargs["crop"] = bool(bit.split("=")[1])

    if len(bits) < 1:
        message = "'%s' tag requires more than 1 argument" % bits[0]
        raise TemplateSyntaxError(message)

    return PhotoImageURL(photo, *args, **kwargs)