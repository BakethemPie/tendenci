# django
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages

from base.http import Http403
from pages.models import Page
from pages.forms import PageForm
from perms.models import ObjectPermission
from event_logs.models import EventLog
from meta.models import Meta as MetaTags
from meta.forms import MetaForm
from perms.utils import get_notice_recipients
from perms.utils import is_admin
from perms.utils import has_perm

try:
    from notification import models as notification
except:
    notification = None

def index(request, slug=None, template_name="pages/view.html"):
    if not slug: return HttpResponseRedirect(reverse('page.search'))
    page = get_object_or_404(Page, slug=slug)
    
    # non-admin can not view the non-active content
    # status=0 has been taken care of in the has_perm function
    if (page.status_detail).lower() <> 'active' and (not is_admin(request.user)):
        raise Http403

    if has_perm(request.user,'pages.view_page',page):
        log_defaults = {
            'event_id' : 585000,
            'event_data': '%s (%d) viewed by %s' % (page._meta.object_name, page.pk, request.user),
            'description': '%s viewed' % page._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': page,
        }
        EventLog.objects.log(**log_defaults)        
        
        return render_to_response(template_name, {'page': page}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def search(request, template_name="pages/search.html"):
    query = request.GET.get('q', None)
    pages = Page.objects.search(query, user=request.user)
    pages = pages.order_by('-create_dt')

    log_defaults = {
        'event_id' : 584000,
        'event_data': '%s searched by %s' % ('Page', request.user),
        'description': '%s searched' % 'Page',
        'user': request.user,
        'request': request,
        'source': 'pages'
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(template_name, {'pages':pages}, 
        context_instance=RequestContext(request))

def print_view(request, slug, template_name="pages/print-view.html"):
    
    page = get_object_or_404(Page, slug=slug)

    if has_perm(request.user,'pages.view_page',page):
        log_defaults = {
            'event_id' : 585001,
            'event_data': '%s (%d) viewed by %s' % (page._meta.object_name, page.pk, request.user),
            'description': '%s viewed - print view' % page._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': page,
        }
        EventLog.objects.log(**log_defaults)
        return render_to_response(template_name, {'page': page}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def edit(request, id, form_class=PageForm, template_name="pages/edit.html"):

    page = get_object_or_404(Page, pk=id)

    if has_perm(request.user,'pages.change_page',page):    
        if request.method == "POST":
            form = form_class(request.POST, instance=page, user=request.user)
            if form.is_valid():
                page = form.save(commit=False)

                # set up user permission
                page.allow_user_view, page.allow_user_edit = form.cleaned_data['user_perms']
                
                # assign permissions
                ObjectPermission.objects.remove_all(page)
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], page)
                ObjectPermission.objects.assign(page.creator, page) 
                
                page.save()

                log_defaults = {
                    'event_id' : 582000,
                    'event_data': '%s (%d) edited by %s' % (page._meta.object_name, page.pk, request.user),
                    'description': '%s edited' % page._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': page,
                }
                EventLog.objects.log(**log_defaults)               
  
                messages.add_message(request, messages.INFO, 'Successfully updated %s' % page)
                
                if not is_admin(request.user):
                    # send notification to administrators
                    recipients = get_notice_recipients('module', 'pages', 'pagerecipients')
                    if recipients:
                        if notification:
                            extra_context = {
                                'object': page,
                                'request': request,
                            }
                            notification.send_emails(recipients,'page_edited', extra_context)
                                                              
                return HttpResponseRedirect(reverse('page', args=[page.slug]))             
        else:
            form = form_class(instance=page, user=request.user)

        return render_to_response(template_name, {'page': page, 'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def edit_meta(request, id, form_class=MetaForm, template_name="pages/edit-meta.html"):

    # check permission
    page = get_object_or_404(Page, pk=id)
    if not has_perm(request.user,'pages.change_page',page):
        raise Http403

    defaults = {
        'title': page.get_title(),
        'description': page.get_description(),
        'keywords': page.get_keywords(),
        'canonical_url': page.get_canonical_url(),
    }
    page.meta = MetaTags(**defaults)

    if request.method == "POST":
        form = form_class(request.POST, instance=page.meta)
        if form.is_valid():
            page.meta = form.save() # save meta
            page.save() # save relationship

            messages.add_message(request, messages.INFO, 'Successfully updated meta for %s' % page)
            
            return HttpResponseRedirect(reverse('page', args=[page.slug]))
    else:
        form = form_class(instance=page.meta)

    return render_to_response(template_name, {'page': page, 'form':form}, 
        context_instance=RequestContext(request))

@login_required
def add(request, form_class=PageForm, template_name="pages/add.html"):

    if has_perm(request.user,'pages.add_page'):
        if request.method == "POST":
            form = form_class(request.POST, user=request.user)
            if form.is_valid():           
                page = form.save(commit=False)
                
                # set up the user information
                page.creator = request.user
                page.creator_username = request.user.username
                page.owner = request.user
                page.owner_username = request.user.username
                
                # set up user permission
                page.allow_user_view, page.allow_user_edit = form.cleaned_data['user_perms']
                
                page.save() # get pk

                # assign permissions for selected groups
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], page)
                # assign creator permissions
                ObjectPermission.objects.assign(page.creator, page) 

                page.save() # update search-index w/ permissions
 
                log_defaults = {
                    'event_id' : 581000,
                    'event_data': '%s (%d) added by %s' % (page._meta.object_name, page.pk, request.user),
                    'description': '%s added' % page._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': page,
                }
                EventLog.objects.log(**log_defaults)
                
                messages.add_message(request, messages.INFO, 'Successfully added %s' % page)
                
                if not is_admin(request.user):
                    # send notification to administrators
                    recipients = get_notice_recipients('module', 'pages', 'pagerecipients')
                    if recipients:
                        if notification:
                            extra_context = {
                                'object': page,
                                'request': request,
                            }
                            notification.send_emails(recipients,'page_added', extra_context)
                    
                return HttpResponseRedirect(reverse('page', args=[page.slug]))
        else:
            form = form_class(user=request.user)
           
        return render_to_response(template_name, {'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def delete(request, id, template_name="pages/delete.html"):
    page = get_object_or_404(Page, pk=id)

    if has_perm(request.user,'pages.delete_page'):   
        if request.method == "POST":
            log_defaults = {
                'event_id' : 583000,
                'event_data': '%s (%d) deleted by %s' % (page._meta.object_name, page.pk, request.user),
                'description': '%s deleted' % page._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': page,
            }
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.INFO, 'Successfully deleted %s' % page)
            
            # send notification to administrators
            recipients = get_notice_recipients('module', 'pages', 'pagerecipients')
            if recipients:
                if notification:
                    extra_context = {
                        'object': page,
                        'request': request,
                    }
                    notification.send_emails(recipients,'page_deleted', extra_context)
            
            page.delete()
            return HttpResponseRedirect(reverse('page.search'))
    
        return render_to_response(template_name, {'page': page}, 
            context_instance=RequestContext(request))
    else:
        raise Http403