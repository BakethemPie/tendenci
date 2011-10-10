from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib import messages
from django.http import HttpResponse
from django.forms.models import modelformset_factory
from django.utils import simplejson as json

from base.http import Http403
from event_logs.models import EventLog
from perms.utils import has_perm, update_perms_and_save, is_admin
from pages.models import Page
from navs.models import Nav, NavItem
from navs.forms import NavForm, PageSelectForm, ItemForm
from navs.utils import cache_nav

@login_required
def search(request, template_name="navs/search.html"):
    query = request.GET.get('q', None)
    navs = Nav.objects.search(query, user=request.user)
    
    log_defaults = {
        'event_id' : 195400,
        'event_data': '%s searched by %s' % ('Nav', request.user),
        'description': '%s searched' % 'Nav',
        'user': request.user,
        'request': request,
        'source': 'navs'
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(
        template_name,
        {'navs':navs},
        context_instance=RequestContext(request)
    )

@login_required
def detail(request, id, template_name="navs/detail.html"):
    nav = get_object_or_404(Nav, id=id)
    
    if not has_perm(request.user, 'navs.view_nav', nav):
        raise Http403
        
    log_defaults = {
        'event_id': 195500,
        'event_data': '%s (%d) viewed by %s' % (
             nav._meta.object_name,
             nav.pk, request.user
        ),
        'description': '%s viewed' % nav._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': nav,
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(
        template_name,
        {'nav':nav},
        context_instance=RequestContext(request),
    )

@login_required
def add(request, form_class=NavForm, template_name="navs/add.html"):
    if not has_perm(request.user, 'navs.add_nav'):
        raise Http403
    
    if request.method == "POST":
        form = form_class(request.POST, user=request.user)
        if form.is_valid():
            nav = form.save(commit=False)
            nav = update_perms_and_save(request, form, nav)
            log_defaults = {
                    'event_id' : 195100,
                    'event_data': '%s (%d) added by %s' % (nav._meta.object_name, nav.pk, request.user),
                    'description': '%s added' % nav._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': nav,
                }
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.INFO, 'Successfully added %s' % nav)
            return redirect('navs.edit_items', id=nav.id)
    else:
        form = form_class(user=request.user)
        
    return render_to_response(
        template_name,
        {'form':form},
        context_instance=RequestContext(request),
    )

@login_required
def edit(request, id, form_class=NavForm, template_name="navs/edit.html"):
    nav = get_object_or_404(Nav, id=id)
    if not has_perm(request.user, 'navs.change_nav', nav):
        raise Http403
    
    if request.method == "POST":
        form = form_class(request.POST, instance=nav, user=request.user)
        if form.is_valid():
            nav = form.save(commit=False)
            nav = update_perms_and_save(request, form, nav)
            cache_nav(nav)
            log_defaults = {
                    'event_id' : 195200,
                    'event_data': '%s (%d) updated by %s' % (nav._meta.object_name, nav.pk, request.user),
                    'description': '%s updated' % nav._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': nav,
                }
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.INFO, 'Successfully updated %s' % nav)
            return redirect('navs.edit_items', id=nav.id)
    else:
        form = form_class(user=request.user, instance=nav)
        
    return render_to_response(
        template_name,
        {'form':form, 'nav':nav},
        context_instance=RequestContext(request),
    )

@login_required
def edit_items(request, id, template_name="navs/nav_items.html"):
    nav = get_object_or_404(Nav, id=id)
    if not has_perm(request.user, 'navs.change_nav', nav):
        raise Http403
    
    ItemFormSet = modelformset_factory(NavItem,
                        form=ItemForm,
                        extra=0,
                        can_delete=True)
    page_select = PageSelectForm()
    
    if request.method == "POST":
        formset = ItemFormSet(request.POST, queryset=nav.navitem_set.all().order_by('ordering'))
        if formset.is_valid():
            old_items = nav.navitem_set.all()
            items = formset.save(commit=False)
            # update or create nav items
            for item in items:
                item.nav = nav
                item.save()
            # delete items no removed from the formset
            for old_item in old_items:
                if not(old_item in items):
                    old_item.delete()
            cache_nav(nav)
            messages.add_message(request, messages.INFO, 'Successfully updated %s' % nav)
            return redirect('navs.tag_test', id=nav.id)
    else:
        formset = ItemFormSet(queryset=nav.navitem_set.all().order_by('ordering'))
        
    return render_to_response(
        template_name,
        {'page_select':page_select, 'formset':formset, 'nav':nav},
        context_instance=RequestContext(request),
    )

@login_required
def page_select(request, form_class=PageSelectForm):
    if not is_admin(request.user):
        raise Http403
    
    if request.method=="POST":
        form = form_class(request.POST)
        if form.is_valid():
            pages = form.cleaned_data['pages']
            infos = []
            for page in pages:
                infos.append({
                    "url":page.get_absolute_url(),
                    "label":page.title,
                    "id":page.id,
                })
            return HttpResponse(json.dumps({
                "pages": infos,
            }), mimetype="text/plain")
    return HttpResponse(json.dumps({
                "error": True
            }), mimetype="text/plain")

def tag_test(request, id, template_name="navs/preview_nav.html"):
    nav = get_object_or_404(Nav, id=id)
    return render_to_response(
        template_name,
        {'nav':nav},
        context_instance=RequestContext(request),
    )
