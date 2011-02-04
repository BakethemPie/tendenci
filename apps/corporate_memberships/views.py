from datetime import datetime, date
#from django.conf import settings
#from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from base.http import Http403
from perms.utils import has_perm, is_admin

from event_logs.models import EventLog

from corporate_memberships.models import CorpApp, CorpField, CorporateMembership, CorporateMembershipType
from corporate_memberships.models import CorporateMembershipRep
from corporate_memberships.forms import CorpMembForm, CorpMembRepForm
from corporate_memberships.utils import get_corporate_membership_type_choices, get_payment_method_choices
from corporate_memberships.utils import corp_memb_inv_add
#from memberships.models import MembershipType

from perms.utils import get_notice_recipients
try:
    from notification import models as notification
except:
    notification = None


def add(request, slug, template="corporate_memberships/add.html"):
    """
        add a corporate membership
    """ 
    corp_app = get_object_or_404(CorpApp, slug=slug)
    user_is_admin = is_admin(request.user)
    
    # if app requires login and they are not logged in, 
    # prompt them to log in and redirect them back to this add page
    if not request.user.is_authenticated():
        messages.add_message(request, messages.INFO, 'Please log in or sign up to the site before signing up the corporate membership.')
        return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), reverse('corp_memb.add', args=[corp_app.slug])))
    
    if not user_is_admin and corp_app.status <> 1 and corp_app.status_detail <> 'active':
        raise Http403

    #if not has_perm(request.user,'corporate_memberships.view_corpapp',corp_app):
    #    raise Http403
    
    field_objs = corp_app.fields.filter(visible=1)
    if not user_is_admin:
        field_objs = field_objs.filter(admin_only=0)
    
    field_objs = list(field_objs.order_by('order'))
    
    form = CorpMembForm(corp_app, field_objs, request.POST or None, request.FILES or None)
    
    # corporate_membership_type choices
    form.fields['corporate_membership_type'].choices = get_corporate_membership_type_choices(request.user, corp_app)
    
    form.fields['payment_method'].choices = get_payment_method_choices(request.user)
    
    # add an admin only block for admin
    if user_is_admin:
        field_objs.append(CorpField(label='Admin Only', field_type='section_break', admin_only=1))
        field_objs.append(CorpField(label='Join Date', field_name='join_dt', admin_only=1))
        field_objs.append(CorpField(label='Status', field_name='status', admin_only=1))
        field_objs.append(CorpField(label='status_detail', field_name='status_detail', admin_only=1))
    else:
        del form.fields['join_dt']
        del form.fields['status']
        del form.fields['status_detail']
    del form.fields['expiration_dt']
    
    # captcha
    #if corp_app.use_captcha and (not request.user.is_authenticated()):
    #    field_objs.append(CorpField(label='Type the code below', field_name='captcha'))
    #else:
    #    del form.fields['captcha']
    
    if request.method == "POST":
        if form.is_valid():
            corporate_membership = form.save(request.user)
            
            # calculate the expiration
            memb_type = corporate_membership.corporate_membership_type.membership_type
            corporate_membership.expiration_dt = memb_type.get_expiration_dt(join_dt=corporate_membership.join_dt)
            corporate_membership.save()
            
            # generate invoice
            corp_memb_inv_add(request.user, corporate_membership)
            
            # send notification to administrators
            recipients = get_notice_recipients('module', 'corporatememberships', 'corporatemembershiprecipients')
            if recipients:
                if notification:
                    extra_context = {
                        'object': corporate_membership,
                        'request': request,
                    }
                    notification.send_emails(recipients,'corp_memb_added', extra_context)
            
            
            # log an event
            log_defaults = {
                'event_id' : 681000,
                'event_data': '%s (%d) added by %s' % (corporate_membership._meta.object_name, 
                                                       corporate_membership.pk, request.user),
                'description': '%s added' % corporate_membership._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': corporate_membership,
            }
            EventLog.objects.log(**log_defaults)
            
            # handle online payment
            if corporate_membership.payment_method.lower() in ['credit card', 'cc']:
                if corporate_membership.invoice and corporate_membership.invoice.balance > 0:
                    return HttpResponseRedirect(reverse('payments.views.pay_online', args=[corporate_membership.invoice.id, corporate_membership.invoice.guid])) 
            
            return HttpResponseRedirect(reverse('corp_memb.add_conf', args=[corporate_membership.id]))
        
    context = {"corp_app": corp_app, "field_objs": field_objs, 'form':form}
    return render_to_response(template, context, RequestContext(request))

def add_conf(request, id, template="corporate_memberships/add_conf.html"):
    """
        add a corporate membership
    """ 
    corporate_membership = get_object_or_404(CorporateMembership, id=id)
    
    if not has_perm(request.user,'corporate_memberships.view_corporatemembership',corporate_membership):
        raise Http403
    
    context = {"corporate_membership": corporate_membership}
    return render_to_response(template, context, RequestContext(request))

@login_required
def edit(request, id, template="corporate_memberships/edit.html"):
    """
        edit a corporate membership
    """ 
    corporate_membership = get_object_or_404(CorporateMembership, id=id)
    
    if not has_perm(request.user,'corporate_memberships.change_corporatemembership',corporate_membership):
        raise Http403
    
    user_is_admin = is_admin(request.user)
    
    corp_app = corporate_membership.corp_app
    
    # get the list of field objects for this corporate membership
    field_objs = corp_app.fields.filter(visible=1)
    if not user_is_admin:
        field_objs = field_objs.filter(admin_only=0)
    
    field_objs = list(field_objs.order_by('order'))
    
    # get the field entry for each field_obj if exists
    for field_obj in field_objs:
        field_obj.entry = field_obj.get_entry(corporate_membership)
        
    form = CorpMembForm(corporate_membership.corp_app, field_objs, request.POST or None, 
                        request.FILES or None, instance=corporate_membership)
    
    # add or delete fields based on the security level
    if user_is_admin:
        field_objs.append(CorpField(label='Admin Only', field_type='section_break', admin_only=1))
        field_objs.append(CorpField(label='Join Date', field_name='join_dt', admin_only=1))
        field_objs.append(CorpField(label='Expiration Date', 
                                    field_name='expiration_dt', 
                                    admin_only=1))
        field_objs.append(CorpField(label='Status', field_name='status', admin_only=1))
        field_objs.append(CorpField(label='status_detail', field_name='status_detail', admin_only=1))
    else:
        del form.fields['join_dt']
        del form.fields['expiration_dt']
        del form.fields['status']
        del form.fields['status_detail']
       
    
    # corporate_membership_type choices
    form.fields['corporate_membership_type'].choices = get_corporate_membership_type_choices(request.user, 
                                                                                corp_app)
    
    form.fields['payment_method'].choices = get_payment_method_choices(request.user)
    
    # we don't need the captcha on edit because it requires login
    #del form.fields['captcha']
        
        
    if request.method == "POST":
        if form.is_valid():
            corporate_membership = form.save(request.user)
            
            # send notification to administrators
            if not user_is_admin:
                recipients = get_notice_recipients('module', 'corporate_membership', 'corporatemembershiprecipients')
                if recipients:
                    if notification:
                        extra_context = {
                            'object': corporate_membership,
                            'request': request,
                        }
                        notification.send_emails(recipients,'corp_memb_edited', extra_context)
            
            # log an event
            log_defaults = {
                'event_id' : 682000,
                'event_data': '%s (%d) edited by %s' % (corporate_membership._meta.object_name, 
                                                       corporate_membership.pk, request.user),
                'description': '%s edited' % corporate_membership._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': corporate_membership,
            }
            EventLog.objects.log(**log_defaults)
            
            
            return HttpResponseRedirect(reverse('corp_memb.view', args=[corporate_membership.id]))
            
            
    
    context = {"corporate_membership": corporate_membership, 
               'corp_app': corp_app,
               'field_objs': field_objs, 
               'form':form}
    return render_to_response(template, context, RequestContext(request))



def view(request, id, template="corporate_memberships/view.html"):
    """
        view a corporate membership
    """  
    corporate_membership = get_object_or_404(CorporateMembership, id=id)
    
    if not has_perm(request.user,'corporate_memberships.view_corporatemembership',corporate_membership):
        raise Http403
    
    can_edit = False
    if has_perm(request.user,'corporate_memberships.edit_corporatemembership',corporate_membership):
        can_edit = True
    
    user_is_admin = is_admin(request.user)
    
    field_objs = corporate_membership.corp_app.fields.filter(visible=1)
    if not user_is_admin:
        field_objs = field_objs.filter(admin_only=0)
    
    field_objs = list(field_objs.order_by('order'))
    
    if can_edit:
        field_objs.append(CorpField(label='Representatives', field_type='section_break', admin_only=0))
        field_objs.append(CorpField(label='Reps', field_name='reps', object_type='corporate_membership', admin_only=0))
        
        
    if user_is_admin:
        field_objs.append(CorpField(label='Admin Only', field_type='section_break', admin_only=1))
        field_objs.append(CorpField(label='Join Date', field_name='join_dt', object_type='corporate_membership', admin_only=1))
        field_objs.append(CorpField(label='Expiration Date', field_name='expiration_dt', object_type='corporate_membership', admin_only=1))
        field_objs.append(CorpField(label='Status', field_name='status', object_type='corporate_membership', admin_only=1))
        field_objs.append(CorpField(label='Status Detail', field_name='status_detail', object_type='corporate_membership', admin_only=1))
        
    for field_obj in field_objs:
        field_obj.value = field_obj.get_value(corporate_membership)
        if isinstance(field_obj.value, datetime) or isinstance(field_obj.value, date):
            field_obj.is_date = True
        else:
            field_obj.is_date = False
            
    
    context = {"corporate_membership": corporate_membership, 'field_objs': field_objs}
    return render_to_response(template, context, RequestContext(request))


def search(request, template_name="corporate_memberships/search.html"):
    query = request.GET.get('q', None)
    corp_members = CorporateMembership.objects.search(query)
    if is_admin(request.user):
        corp_members = corp_members.order_by('name_exact')
    else:
        if request.user.is_authenticated():
            from django.db.models import Q
            corp_members = corp_members.objects.filter(Q(creator=request.user) | 
                                                       Q(owner=request.user) | 
                                                       Q(status_detail='active'))
            corp_members = corp_members.order_by('name_exact')
        else:
            raise Http403
    
    return render_to_response(template_name, {'corp_members': corp_members}, 
        context_instance=RequestContext(request))
    
    
@login_required
def delete(request, id, template_name="corporate_memberships/delete.html"):
    corp_memb = get_object_or_404(CorporateMembership, pk=id)

    if has_perm(request.user,'corporate_memberships.delete_corporatemembership'):   
        if request.method == "POST":
            log_defaults = {
                'event_id' : 683000,
                'event_data': '%s (%d) deleted by %s' % (corp_memb._meta.object_name, corp_memb.pk, request.user),
                'description': '%s deleted' % corp_memb._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': corp_memb,
            }
            
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.INFO, 'Successfully deleted %s' % corp_memb)
            
#            # send notification to administrators
#            recipients = get_notice_recipients('module', 'corporate_membership', 'corporatemembershiprecipients')
#            if recipients:
#                if notification:
#                    extra_context = {
#                        'object': corp_memb,
#                        'request': request,
#                    }
#                    notification.send_emails(recipients,'corp_memb_deleted', extra_context)
#            
            corp_memb.delete()
                
            return HttpResponseRedirect(reverse('corp_memb.search'))
    
        return render_to_response(template_name, {'corp_memb': corp_memb}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
    
    
def index(request, template_name="corporate_memberships/index.html"):
    corp_apps = CorpApp.objects.filter(status=1, status_detail='active').order_by('name')
    #cm_types = CorporateMembershipType.objects.filter(status=1, status_detail='active').order_by('-price')
    
    return render_to_response(template_name, {'corp_apps': corp_apps}, 
        context_instance=RequestContext(request))
    
    
def edit_reps(request, id, form_class=CorpMembRepForm, template_name="corporate_memberships/edit_reps.html"):
    corp_memb = get_object_or_404(CorporateMembership, pk=id)
    
    if not has_perm(request.user,'corporate_memberships.change_corporatemembership',corp_memb):
        raise Http403
    
    reps = CorporateMembershipRep.objects.filter(corporate_membership=corp_memb).order_by('user')
    form = form_class(corp_memb, request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            rep = form.save(commit=False)
            rep.corporate_membership = corp_memb
            rep.save()
            
            # log an event here
            
            if (request.POST.get('submit', '')).lower() == 'save':
                return HttpResponseRedirect(reverse('corp_memb.view', args=[corp_memb.id]))

    
    return render_to_response(template_name, {'corp_memb': corp_memb, 
                                              'form': form,
                                              'reps': reps}, 
        context_instance=RequestContext(request))
    
    
@login_required
def delete_rep(request, id, template_name="corporate_memberships/delete_rep.html"):
    rep = get_object_or_404(CorporateMembershipRep, pk=id)
    corp_memb = rep.corporate_membership

    if has_perm(request.user,'corporate_memberships.edit_corporatemembership'):   
        if request.method == "POST":
            
            messages.add_message(request, messages.INFO, 'Successfully deleted %s' % rep)
            
            rep.delete()
                
            return HttpResponseRedirect(reverse('corp_memb.edit_reps', args=[corp_memb.pk]))
    
        return render_to_response(template_name, {'corp_memb': rep}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
    
    


