from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages

from base.http import Http403
from base.utils import now_localized
from models import Service
from forms import ServiceForm
from perms.object_perms import ObjectPermission
from perms.utils import get_notice_recipients, is_admin
from perms.utils import has_perm
from event_logs.models import EventLog
from meta.models import Meta as MetaTags
from meta.forms import MetaForm

try:
    from notification import models as notification
except:
    notification = None

def index(request, slug=None, template_name="services/view.html"):
    if not slug: return HttpResponseRedirect(reverse('service.search'))
    service = get_object_or_404(Service, slug=slug)
    
    if has_perm(request.user,'services.view_service',service):
        log_defaults = {
            'event_id' : 355000,
            'event_data': '%s (%d) viewed by %s' % (service._meta.object_name, service.pk, request.user),
            'description': '%s viewed' % service._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': service,
        }
        #EventLog.objects.log(**log_defaults)
        return render_to_response(template_name, {'service': service}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def search(request, template_name="services/search.html"):
    query = request.GET.get('q', None)
    services = Service.objects.search(query, user=request.user)
    services = services.order_by('-create_dt')

    log_defaults = {
        'event_id' : 354000,
        'event_data': '%s searched by %s' % ('Service', request.user),
        'description': '%s searched' % 'service',
        'user': request.user,
        'request': request,
        'source': 'services'
    }
    #EventLog.objects.log(**log_defaults)
    
    return render_to_response(template_name, {'services':services}, 
        context_instance=RequestContext(request))

def print_view(request, slug, template_name="services/print-view.html"):
    service = get_object_or_404(Service, slug=slug)    

    log_defaults = {
        'event_id' : 355001,
        'event_data': '%s (%d) viewed by %s' % (service._meta.object_name, service.pk, request.user),
        'description': '%s viewed - print view' % service._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': service,
    }
    #EventLog.objects.log(**log_defaults)
       
    if has_perm(request.user,'services.view_service', service):
        return render_to_response(template_name, {'service': service}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def add(request, form_class=ServiceForm, template_name="services/add.html"):
    if request.method == "POST":
        form = form_class(request.POST, user=request.user)
        if form.is_valid():
            service = form.save(commit=False)
            
            # set it to pending if the user is anonymous
            if not request.user.is_authenticated():
                service.status = 0
                service.status_detail = 'pending'

            # set up the expiration time based on requested duration
            now = now_localized()
            service.expiration_dt = now + timedelta(days=service.requested_duration)

            # set up the user information
            if request.user.is_authenticated():
                service.creator = request.user
                service.creator_username = request.user.username
                service.owner = request.user
                service.owner_username = request.user.username

            # set up user permission
            if request.user.is_authenticated():
                service.allow_user_view, service.allow_user_edit = form.cleaned_data['user_perms']
            else:
                service.allow_anonymous_view = False
                service.allow_user_view = False
                service.allow_user_edit = False

            service.save() # get pk

            if request.user.is_authenticated():
                # assign permissions for selected groups
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], service)
                # assign creator permissions
                ObjectPermission.objects.assign(service.creator, service)

            service.save() # update search-index w/ permissions

            log_defaults = {
                'event_id' : 351000,
                'event_data': '%s (%d) added by %s' % (service._meta.object_name, service.pk, request.user),
                'description': '%s added' % service._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': service,
            }
            #EventLog.objects.log(**log_defaults)

            if request.user.is_authenticated():
                messages.add_message(request, messages.INFO, 'Successfully added %s' % service)

            # send notification to administrators
            recipients = get_notice_recipients('module', 'services', 'servicerecipients')
            if recipients:
                if notification:
                    extra_context = {
                        'object': service,
                        'request': request,
                    }
                    notification.send_emails(recipients,'service_added', extra_context)

            if not request.user.is_authenticated():
                return HttpResponseRedirect(reverse('service.thank_you'))
            else:
                return HttpResponseRedirect(reverse('service', args=[service.slug]))
    else:
        form = form_class(user=request.user)

    return render_to_response(template_name, {'form':form},
        context_instance=RequestContext(request))

@login_required
def edit(request, id, form_class=ServiceForm, template_name="services/edit.html"):
    service = get_object_or_404(Service, pk=id)

    if has_perm(request.user,'services.change_service',service):    
        if request.method == "POST":
            form = form_class(request.POST, instance=service, user=request.user)
            if form.is_valid():
                service = form.save(commit=False)

                # set up user permission
                service.allow_user_view, service.allow_user_edit = form.cleaned_data['user_perms']

                # assign permissions
                ObjectPermission.objects.remove_all(service)
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], service)
                ObjectPermission.objects.assign(service.creator, service)

                service.save()

                log_defaults = {
                    'event_id' : 352000,
                    'event_data': '%s (%d) edited by %s' % (service._meta.object_name, service.pk, request.user),
                    'description': '%s edited' % service._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': service,
                }
                EventLog.objects.log(**log_defaults) 
                
                messages.add_message(request, messages.INFO, 'Successfully updated %s' % service)
                                                              
                return HttpResponseRedirect(reverse('service', args=[service.slug]))             
        else:
            form = form_class(instance=service, user=request.user)

        return render_to_response(template_name, {'service': service, 'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def edit_meta(request, id, form_class=MetaForm, template_name="services/edit-meta.html"):

    # check permission
    service = get_object_or_404(Service, pk=id)
    if not has_perm(request.user,'services.change_service',service):
        raise Http403

    defaults = {
        'title': service.get_title(),
        'description': service.get_description(),
        'keywords': service.get_keywords(),
        'canonical_url': service.get_canonical_url(),
    }
    service.meta = MetaTags(**defaults)


    if request.method == "POST":
        form = form_class(request.POST, instance=service.meta)
        if form.is_valid():
            service.meta = form.save() # save meta
            service.save() # save relationship

            messages.add_message(request, messages.INFO, 'Successfully updated meta for %s' % service)
            
            return HttpResponseRedirect(reverse('service', args=[service.slug]))
    else:
        form = form_class(instance=service.meta)

    return render_to_response(template_name, {'service': service, 'form':form}, 
        context_instance=RequestContext(request))

@login_required
def delete(request, id, template_name="services/delete.html"):
    service = get_object_or_404(service, pk=id)

    if has_perm(request.user,'services.delete_service'):   
        if request.method == "POST":
            log_defaults = {
                'event_id' : 433000,
                'event_data': '%s (%d) deleted by %s' % (service._meta.object_name, service.pk, request.user),
                'description': '%s deleted' % service._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': service,
            }
            
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.INFO, 'Successfully deleted %s' % service)
            
            # send notification to administrators
            recipients = get_notice_recipients('module', 'services', 'servicerecipients')
            if recipients:
                if notification:
                    extra_context = {
                        'object': service,
                        'request': request,
                    }
                    notification.send_emails(recipients,'service_deleted', extra_context)
            
            service.delete()
                
            return HttpResponseRedirect(reverse('service.search'))
    
        return render_to_response(template_name, {'service': service}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def pending(request, template_name="services/pending.html"):
    if not is_admin(request.user):
        raise Http403
    services = Service.objects.filter(status=0, status_detail='pending')
    return render_to_response(template_name, {'services': services},
            context_instance=RequestContext(request))

def approve(request, id, template_name="services/approve.html"):
    if not is_admin(request.user):
        raise Http403
    service = get_object_or_404(Service, pk=id)

    if request.method == "POST":
        service.activation_dt = now_localized()
        service.allow_anonymous_view = True
        service.status = True
        service.status_detail = 'active'

        if not service.creator:
            service.creator = request.user
            service.creator_username = request.user.username

        if not service.owner:
            service.owner = request.user
            service.owner_username = request.user.username

        service.save()

        messages.add_message(request, messages.INFO, 'Successfully approved %s' % service)

        return HttpResponseRedirect(reverse('service', args=[service.slug]))

    return render_to_response(template_name, {'service': service},
            context_instance=RequestContext(request))

def thank_you(request, template_name="services/thank-you.html"):
    return render_to_response(template_name, {}, context_instance=RequestContext(request))