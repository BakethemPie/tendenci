from django.template import Library

register = Library()

@register.inclusion_tag("corporate_memberships/render_corp_field.html")
def render_corp_field(request, field_obj, form):
    if field_obj.field_type == "section_break" or field_obj.field_type == "page_break":
        field = None
    else:
        field_name = field_obj.field_name
        if not field_name: 
            field_name = "field_%s" % field_obj.id
        field = eval("form['%s']" % field_name)
    return {'request':request, 'field_obj':field_obj, 'field':field}
