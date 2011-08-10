import os
from django.template import loader, TemplateDoesNotExist
from django.template.loader import get_template, Template
from django.http import HttpResponse
from django.conf import settings

def themed_response(*args, **kwargs):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    
    """
    httpresponse_kwargs = {'mimetype': kwargs.pop('mimetype', None)}
    return HttpResponse(render_to_theme(*args, **kwargs), **httpresponse_kwargs)
    
def render_to_theme(template_name, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders it with the given dictionary as
    context. The template_name may be a string to load a single template using
    get_template, or it may be a tuple to use select_template to find one of
    the templates in the list. Returns a string.
    This shorcut prepends the template_name given with the selected theme's 
    directory
    """
    dictionary = dictionary or {}
    
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    
    theme = context_instance['THEME']
        
    if isinstance(template_name, (list, tuple)):
        try:
            t = select_template("%s/templates/%s" % (theme, template_name))
        except TemplateDoesNotExist:
            t = Template(unicode(file(os.path.join(settings.PROJECT_ROOT, "templates",template_name)).read(), "utf-8"))
    else:
        try:
            t = get_template("%s/templates/%s" % (theme, template_name))
        except TemplateDoesNotExist:
            t = Template(unicode(file(os.path.join(settings.PROJECT_ROOT, "templates", template_name)).read(), "utf-8"))
    return t.render(context_instance)
