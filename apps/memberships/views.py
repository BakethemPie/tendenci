import os
import sys
import hashlib
from hashlib import md5

from datetime import datetime, timedelta
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType, ContentTypeManager
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.template.defaultfilters import slugify
from event_logs.models import EventLog
from base.http import Http403
from memberships.models import App, AppEntry, Membership, \
    MembershipType, Notice, AppField, AppFieldEntry
from memberships.forms import AppForm, AppEntryForm, \
    AppCorpPreForm, MemberApproveForm, CSVForm, ReportForm, EntryEditForm, \
    ExportForm
from memberships.utils import new_mems_from_csv, is_import_valid
from user_groups.models import GroupMembership
from perms.utils import get_notice_recipients, \
    has_perm, update_perms_and_save, is_admin, is_member, is_developer
from invoices.models import Invoice
from corporate_memberships.models import CorporateMembership, IndivMembEmailVeri8n
from geraldo.generators import PDFGenerator
from reports import ReportNewMems
from files.models import File
from imports.utils import render_excel

try:
    from notification import models as notification
except:
    notification = None
from base.utils import send_email_notification

def membership_index(request):
    return HttpResponseRedirect(reverse('membership.search'))

def membership_search(request, template_name="memberships/search.html"):
    query = request.GET.get('q', None)
    members = Membership.objects.search(query, user=request.user)
    types = MembershipType.objects.all()

    EventLog.objects.log(**{
        'event_id' : 474000,
        'event_data': '%s searched by %s' % ('Membership', request.user),
        'description': '%s searched' % 'Membership',
        'user': request.user,
        'request': request,
        'source': 'memberships'
    })

    return render_to_response(template_name, {'members': members, 'types': types},
        context_instance=RequestContext(request))    


@login_required
def membership_details(request, id=0, template_name="memberships/details.html"):
    """
    Membership details.
    """
    query = 'pk:%s' % id
    sqs = Membership.objects.search(query, user=request.user)

    if sqs:
        membership = sqs.best_match().object
    else:
        raise Http404

    # log membership details view
    EventLog.objects.log(**{
        'event_id' : 475000,
        'event_data': '%s (%d) viewed by %s' % (membership._meta.object_name, membership.pk, request.user),
        'description': '%s viewed' % membership._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': membership,
    })

    return render_to_response(template_name, {'membership': membership},
        context_instance=RequestContext(request))


def application_details(request, slug=None, cmb_id=None, imv_id=0, imv_guid=None, secret_hash="", 
                        membership_id=0, template_name="memberships/applications/details.html"):
    """
    Display a built membership application and handle submission.
    """
    if not slug: raise Http404
    user = request.user

    # check user permissions / get application QS
    query = '"slug:%s"' % slug
    apps = App.objects.search(query, user=user)

    # get application
    if apps: app = apps.best_match().object
    else: raise Http404

    # if this app is for corporation individuals, redirect them to corp-pre page if
    # they have not passed the security check.
    is_corp_ind = False
    corporate_membership = None
    if hasattr(app, 'corp_app') and app.corp_app:
        if not cmb_id:
            # redirect them to the corp_pre page
            return redirect(reverse('membership.application_details_corp_pre', args=[app.slug]))
        
        is_corp_ind = True
        corporate_membership = get_object_or_404(CorporateMembership, id=cmb_id)
        # check if they have verified their email or entered the secret code
        is_verified = False
        if is_admin(request.user) or app.corp_app.authentication_method == 'admin':
            is_verified = True
        elif app.corp_app.authentication_method == 'email':
            try:
                indiv_veri = IndivMembEmailVeri8n.objects.get(pk=imv_id,
                                                              guid=imv_guid)
                if indiv_veri.verified:
                    is_verified = True
            except IndivMembEmailVeri8n.DoesNotExist:
                pass 
                                                              
        elif app.corp_app.authentication_method == 'secret_code':
            tmp_secret_hash = md5('%s%s' % (corporate_membership.secret_code, 
                                    request.session.get('corp_hash_random_string', ''))).hexdigest()
            if secret_hash == tmp_secret_hash:
                is_verified = True
                                        
        
        if not is_verified:
            return redirect(reverse('membership.application_details_corp_pre', args=[slug]))
#       

    # log application details view
    EventLog.objects.log(**{
        'event_id' : 655000,
        'event_data': '%s (%d) viewed by %s' % (app._meta.object_name, app.pk, user),
        'description': '%s viewed' % app._meta.object_name,
        'user': user,
        'request': request,
        'instance': app,
    })
        

    initial_dict = {}
    if hasattr(user, 'memberships'):
        membership = user.memberships.get_membership()
        user_member_requirements = [
            is_developer(user) == False,
            is_admin(user) == False,
            is_member(user) == True,
        ]

        # deny access to renew memberships
        if all(user_member_requirements):
            initial_dict = membership.get_app_initial()
            if not membership.can_renew():
                return render_to_response("memberships/applications/no-renew.html", {
                    "app": app, "user":user, "membership": membership}, 
                    context_instance=RequestContext(request))

    pending_entries = []

    if hasattr(user, 'appentry_set'):
        pending_entries = user.appentry_set.filter(
            is_approved__isnull = True,  # pending   
        )

        if user.memberships.get_membership():
            pending_entries.filter(
                entry_time__gte = user.memberships.get_membership().subscribe_dt
            )

    app_entry_form = AppEntryForm(
            app, 
            request.POST or None, 
            request.FILES or None, 
            user=user, 
            corporate_membership=corporate_membership,
            initial=initial_dict,
        )

    if request.method == "POST":
        if app_entry_form.is_valid():

            entry = app_entry_form.save(commit=False)
            entry_invoice = entry.save_invoice()


            if user.is_authenticated():  # bind to user
                entry.user = user
                if all(user_member_requirements):  # save as renewal
                    entry.is_renewal = True

            # add all permissions and save the model
            entry = update_perms_and_save(request, app_entry_form, entry)

            # administrators go to approve/disapprove page
            if is_admin(user):
                return redirect(reverse('membership.application_entries', args=[entry.pk]))

            # online payment
            if entry.payment_method and entry.payment_method.is_online:
                return HttpResponseRedirect(reverse(
                    'payments.views.pay_online',
                    args=[entry_invoice.pk, entry_invoice.guid]
                ))

            if not entry.approval_required:

                    entry.approve()

                    membership_total = Membership.objects.filter(status=True, status_detail='active').count()

                    notice_dict = {
                        'notice_time':'attimeof',
                        'notice_type':'join',
                        'status':True,
                        'status_detail':'active',
                    }

                    if entry.is_renewal:
                        notice_dict['notice_type'] = 'renewal'

                    # send email to member
                    for notice in Notice.objects.filter(**notice_dict):

                        notice_requirements = [
                           notice.membership_type == entry.membership_type,
                           notice.membership_type == None, 
                        ]

                        if any(notice_requirements):
                            notification.send_emails([entry.email],'membership_approved_to_member', {
                                'subject': notice.get_subject(entry.membership),
                                'content': notice.get_content(entry.membership),
                            })

                    # send email to admins
                    recipients = get_notice_recipients('site', 'global', 'allnoticerecipients')
                    if recipients and notification:
                        notification.send_emails(recipients,'membership_approved_to_admin', {
                            'object':entry,
                            'request':request,
                            'membership_total':membership_total,
                        })

                    # log - entry approval
                    EventLog.objects.log(**{
                        'event_id' : 1082101,
                        'event_data': '%s (%d) approved by %s' % (entry._meta.object_name, entry.pk, entry.judge),
                        'description': '%s viewed' % entry._meta.object_name,
                        'user': user,
                        'request': request,
                        'instance': entry,
                    })

            # log - entry submission
            EventLog.objects.log(**{
                'event_id' : 1081000,
                'event_data': '%s (%d) submitted by %s' % (entry._meta.object_name, entry.pk, request.user),
                'description': '%s viewed' % entry._meta.object_name,
                'user': user,
                'request': request,
                'instance': entry,
            })

            return redirect(entry.confirmation_url)

    c = {
            'app': app, 
            'app_entry_form': app_entry_form, 
            'pending_entries': pending_entries,
        }
    return render_to_response(template_name, c, 
        context_instance=RequestContext(request))
    
def application_details_corp_pre(request, slug, cmb_id=None, template_name="memberships/applications/details_corp_pre.html"):

    try:
        app = App.objects.get(slug=slug)
    except App.DoesNotExist:
        raise Http404

    if not hasattr(app, 'corp_app'):
        raise Http404
    
    if not app.corp_app:
        raise Http404
        
    
    form = AppCorpPreForm(request.POST or None)
    if is_admin(request.user) or app.corp_app.authentication_method == 'admin':
        del form.fields['secret_code']
        del form.fields['email']
        from utils import get_corporate_membership_choices
        form.fields['corporate_membership_id'].choices = get_corporate_membership_choices()
        if cmb_id:
            form.fields['corporate_membership_id'].initial = cmb_id
        form.auth_method = 'corporate_membership_id'
        
    elif app.corp_app.authentication_method == 'email':
        del form.fields['corporate_membership_id']
        del form.fields['secret_code']
        form.auth_method = 'email'
    else: # secret_code
        del form.fields['corporate_membership_id']
        del form.fields['email']
        form.auth_method = 'secret_code'
        
    if request.method == "POST":
        if form.is_valid():
            # find the corporate_membership_id and redirect to membership.application_details
            if form.auth_method == 'corporate_membership_id':
                corporate_membership_id = form.cleaned_data['corporate_membership_id']
            else:
                corporate_membership_id = form.corporate_membership_id
                
                if form.auth_method == 'email':
                    corp_memb = CorporateMembership.objects.get(pk=corporate_membership_id)
                    try:
                        indiv_veri = IndivMembEmailVeri8n.objects.get(corporate_membership=corp_memb,
                                                                verified_email=form.cleaned_data['email'])
                        if indiv_veri.verified:
                            is_verified = True
                        else:
                            is_verified = False
                    except IndivMembEmailVeri8n.DoesNotExist:
                        print form.cleaned_data['email']
                        is_verified = False
                        indiv_veri = IndivMembEmailVeri8n()
                        indiv_veri.corporate_membership = corp_memb
                        indiv_veri.verified_email = form.cleaned_data['email']
                        if request.user and not request.user.is_anonymous():
                            indiv_veri.creator = request.user
                        indiv_veri.save()
                        
                    # send an email to the user to verify the email address
                    # then redirect them to the verification conf page
                    # they'll need to follow the instruction in the email
                    # to continue to sign up.
                    if not is_verified:
                        recipients = [indiv_veri.verified_email]
                        extra_context = {
                            'object': indiv_veri,
                            'app': app,
                            'corp_memb': corp_memb,
                            'request': request,
                        }
                        send_email_notification('membership_corp_indiv_verify_email', recipients, extra_context)
                        
                        return redirect(reverse('membership.email__to_verify_conf'))
                    else:
                        # the email address is verified
                        return redirect(reverse('membership.application_details_via_corp_domain', 
                                                args=[app.slug, 
                                                indiv_veri.corporate_membership.id,
                                                indiv_veri.pk,
                                                indiv_veri.guid]))
                if form.auth_method == 'secret_code':
                    # secret code hash
                    random_string = User.objects.make_random_password(length=4, allowed_chars='abcdefghjkmnpqrstuvwxyz')
                    request.session['corp_hash_random_string'] = random_string
                    secret_code = form.cleaned_data['secret_code']
                    secret_hash = md5('%s%s' % (secret_code, random_string)).hexdigest()
                    return redirect(reverse('membership.application_details_via_corp_secret_code', 
                                            args=[app.slug, 
                                                corporate_membership_id,
                                                secret_hash]))
                
            
            return redirect(reverse('membership.application_details', args=[app.slug, corporate_membership_id]))
    
    c = {'app': app, "form": form}
    return render_to_response(template_name, c, 
        context_instance=RequestContext(request))
    
def email_to_verify_conf(request, template_name="memberships/applications/email_to_verify_conf.html"):
    return render_to_response(template_name, 
        context_instance=RequestContext(request))
    
def verify_email(request, id=0, guid=None, template_name="memberships/applications/verify_email.html"):
    indiv_veri = get_object_or_404(IndivMembEmailVeri8n, id=id, guid=guid)
    if not indiv_veri.verified:
        indiv_veri.verified = True
        indiv_veri.verified_dt = datetime.now()
        if request.user and not request.user.is_anonymous():
            indiv_veri.updated_by = request.user
            indiv_veri.save()
            
    # let them continue to sign up for membership
    return redirect(reverse('membership.application_details_via_corp_domain', 
                            args=[indiv_veri.corporate_membership.corp_app.memb_app.slug,
                                  indiv_veri.corporate_membership.id,
                                  indiv_veri.pk,
                                  indiv_veri.guid]))
    

def application_confirmation(request, hash=None, template_name="memberships/entries/details.html"):
    """
    Display this confirmation have a membership application is submitted.
    """

    if not hash:
        raise Http404

    query = '"hash:%s"' % hash
    sqs = AppEntry.objects.search(query, user=request.user)

    if sqs:
        entry = sqs[0].object
    else:
        raise Http404

    return render_to_response(template_name, {'is_confirmation':True, 'entry': entry},
        context_instance=RequestContext(request))

@login_required
def application_entries(request, id=None, template_name="memberships/entries/details.html"):
    """
    Displays the details of a membership application entry.
    """

    if not id:
        return redirect(reverse('membership.application_entries_search'))

    # TODO: Not use search but query the database
    # TODO: Needs a manager to query database with permission checks
    query = '"id:%s"' % id
    sqs = AppEntry.objects.search(query, user=request.user)

    if sqs:
        entry = sqs[0].object
    else:
        raise Http404

    # log entry view
    EventLog.objects.log(**{
        'event_id' : 1085000,
        'event_data': '%s (%d) viewed by %s' % (entry._meta.object_name, entry.pk, request.user),
        'description': '%s viewed' % entry._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': entry,
    })

    if request.method == "POST":
        form = MemberApproveForm(entry, request.POST)
        if form.is_valid():

            membership_total = Membership.objects.filter(status=True, status_detail='active').count()

            status = request.POST.get('status', '')
            approve = (status.lower() == 'approve') or (status.lower() == 'approve renewal')

            entry.judge = request.user

            if approve:

                user_pk = int(form.cleaned_data['users'])
                if user_pk:
                    entry.user = User.objects.get(pk=user_pk)
                else:
                    entry.user = User.objects.create_user(**{
                        'username': entry.spawn_username(entry.first_name, entry.last_name),
                        'email': entry.email,
                        'password': hashlib.sha1(entry.email).hexdigest()[:6]
                    })

                    from django.core.mail import send_mail
                    from django.utils.http import int_to_base36
                    from django.contrib.auth.tokens import default_token_generator
                    from site_settings.utils import get_setting
                    token_generator = default_token_generator

                    site_url = get_setting('site', 'global', 'siteurl')
                    site_name = get_setting('site', 'global', 'sitedisplayname')

                    # send new user account welcome email (notification)
                    notification.send_emails([entry.user.email],'user_welcome', {
                        'site_url': site_url,
                        'site_name': site_name,
                        'uid': int_to_base36(entry.user.id),
                        'user': entry.user,
                        'username': entry.user.username,
                        'token': token_generator.make_token(entry.user),
                    })

                # update application, user, 
                # group, membership, and archive
                entry.approve()

                notice_dict = {
                    'notice_time':'attimeof',
                    'notice_type':'join',
                    'status':True,
                    'status_detail':'active',
                }

                if entry.is_renewal:
                    notice_dict['notice_type'] = 'renewal'

                

                # send membership notification(s) (email)
                for notice in Notice.objects.filter(**notice_dict):

                    notice_requirements = [
                       notice.membership_type == entry.membership_type,
                       notice.membership_type == None, 
                    ]

                    if any(notice_requirements):
                        notification.send_emails([entry.email],'membership_approved_to_member', {
                            'subject': notice.get_subject(entry.membership),
                            'content': notice.get_content(entry.membership),
                        })

                # send notification to admin (email)
                recipients = get_notice_recipients('site', 'global', 'allnoticerecipients')
                if recipients and notification:
                    notification.send_emails(recipients,'membership_approved_to_admin', {
                        'object':entry,
                        'request':request,
                        'membership_total':membership_total,
                    })

                # log entry approved
                EventLog.objects.log(**{
                    'event_id' : 1085000,
                    'event_data': '%s (%d) approved by %s' % (entry._meta.object_name, entry.pk, request.user),
                    'description': '%s approved' % entry._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': entry,
                })

            else:  # if not approved
                entry.disapprove()

                # send email to disapproved applicant
                notification.send_emails([entry.email],'membership_disapproved_to_member', {
                    'object':entry,
                    'request':request,
                    'membership_total':membership_total,
                })

                # send email to admins
                recipients = get_notice_recipients('site', 'global', 'allnoticerecipients')
                if recipients and notification:
                    notification.send_emails(recipients,'membership_disapproved_to_admin', {
                        'object': entry,
                        'request': request,
                        'membership_total': membership_total,
                    })

                # log entry disapproved
                EventLog.objects.log(**{
                    'event_id' : 1082102,
                    'event_data': '%s (%d) disapproved by %s' % (entry._meta.object_name, entry.pk, request.user),
                    'description': '%s disapproved' % entry._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': entry,
                })

            return redirect(reverse('membership.application_entries', args=[entry.pk]))

    else:  # if request != POST
        form = MemberApproveForm(entry)

    return render_to_response(template_name, {
        'entry': entry,
        'form': form,
        }, context_instance=RequestContext(request))

@login_required
def entry_edit(request, id=0, template_name="memberships/entries/edit.html"):
    """
    Edit membership application entry page.
    """
    entry = get_object_or_404(AppEntry, id=id)  # exists

    if not is_admin(request.user):
        raise Http303  # not permitted

    # log entry view
    EventLog.objects.log(**{
        'event_id' : 1085000,
        'event_data': '%s (%d) viewed by %s' % (entry._meta.object_name, entry.pk, request.user),
        'description': '%s viewed' % entry._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': entry,
    })

    if request.method == "POST":
        form = EntryEditForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()

            messages.add_message(
                request, 
                messages.INFO, 
                'Entry Sucessfully Updated',
            )

            return redirect(reverse('membership.application_entries', args=[entry.pk]))

    else:
        form = EntryEditForm(instance=entry)

    return render_to_response(template_name, {
        'entry': entry,
        'form': form,
        }, context_instance=RequestContext(request))

@login_required
def application_entries_search(request, template_name="memberships/entries/search.html"):
    """
    Displays a page for searching membership application entries.
    """

    query = request.GET.get('q')
    entries = AppEntry.objects.search(query, user=request.user)
    entries = entries.order_by('-entry_time')

    apps = App.objects.all()
    types = MembershipType.objects.all()

    # log entry search view
    EventLog.objects.log(**{
        'event_id' : 1084000,
        'event_data': '%s searched by %s' % ('Membership Entries', request.user),
        'description': '%s searched' % 'Membership Entries',
        'user': request.user,
        'request': request,
        'source': 'memberships',
    })

    return render_to_response(template_name, {
        'entries':entries,
        'apps':apps,
        'types':types,
        }, context_instance=RequestContext(request))
    
@login_required    
def notice_email_content(request, id, template_name="memberships/notices/email_content.html"):
    if not is_admin(request.user):
        raise Http403
    notice = get_object_or_404(Notice, pk=id)
    
    return render_to_response(template_name, {
        'notice':notice,
        }, context_instance=RequestContext(request))

@login_required
def membership_import(request, step=None):
    """
    Membership Import Wizard: Walks you through a series of steps to upload memberships.
    """
    if not is_admin(request.user):
        raise Http403

    if not step:  # start from beginning
        return redirect('membership_import_upload_file')

    request.session.set_expiry(0)  # expire when browser is closed
    step_numeral, step_name = step

    if step_numeral == 1:  # upload-file
        template_name = 'memberships/import-upload-file.html'
        if request.method == 'POST':
            form = CSVForm(request.POST, request.FILES, step=step)
            if form.is_valid():
                cleaned_data = form.save(step=step)
                app = cleaned_data['app']

                # check import requirements
                saved_files = File.objects.save_files_for_instance(request, Membership)
                file_path = os.path.join(settings.MEDIA_ROOT, str(saved_files[0].file))
                valid_import = is_import_valid(file_path)

                # store session info
                request.session['membership.import.app'] = app
                request.session['membership.import.file_path'] = file_path

                # move to next wizard page
                return redirect('membership_import_map_fields')
        else:  # if not POST
            form = CSVForm(step=step)

        return render_to_response(template_name, {
            'form':form,
            'datetime':datetime,
            }, context_instance=RequestContext(request))

    if step_numeral == 2:  # map-fields
        template_name = 'memberships/import-map-fields.html'
        file_path = request.session.get('membership.import.file_path')
        app = request.session.get('membership.import.app')

        if request.method == 'POST':
            form = CSVForm(
                request.POST,
                request.FILES,
                step=step,
                app=app,
                file_path=file_path
            )

            if form.is_valid():
                cleaned_data = form.save(step=step)
                file_path = request.session.get('membership.import.file_path')

                memberships = new_mems_from_csv(file_path, app, cleaned_data)

                request.session['membership.import.memberships'] = memberships
                request.session['membership.import.fields'] = cleaned_data

                return redirect('membership_import_preview')

        else:  # if not POST
            form = CSVForm(step=step, app=app, file_path=file_path)

        return render_to_response(template_name, {
            'form':form,
            'datetime':datetime,
            }, context_instance=RequestContext(request))

    if step_numeral == 3:  # preview
        template_name = 'memberships/import-preview.html'
        memberships = request.session.get('membership.import.memberships')

        added, skipped = [], []
        for membership in memberships:
            if membership.pk: skipped.append(membership)
            else: added.append(membership)

        return render_to_response(template_name, {
        'memberships':memberships,
        'added': added,
        'skipped': skipped,
        'datetime': datetime,
        }, context_instance=RequestContext(request))

    if step_numeral == 4:  # confirm
        template_name = 'memberships/import-confirm.html'

        app = request.session.get('membership.import.app')
        memberships = request.session.get('membership.import.memberships')
        fields = request.session.get('membership.import.fields')

        if not all([app, memberships, fields]):
            return redirect('membership_import_upload_file')

        added = []
        skipped = []

        for membership in memberships:

            if not membership.pk:  # new membership; no pk

                membership.save()  # create pk

                # create entry
                entry = AppEntry.objects.create(
                    app = app,
                    user = membership.user,
                    entry_time = datetime.now(),
                    membership = membership,  # pk required here
                    is_renewal = membership.renewal,
                    is_approved = True,
                    decision_dt = membership.subscribe_dt,
                    judge = membership.creator,
                    creator=membership.creator,
                    creator_username=membership.creator_username,
                    owner=membership.owner,
                    owner_username=membership.owner_username,
                )

                # create entry fields
                for key, value in fields.items():
                    app_fields = AppField.objects.filter(app=app, label=key)
                    if app_fields and membership.m.get(value):
                        AppFieldEntry.objects.create(
                            entry=entry,
                            field=app_fields[0],
                            value=membership.m.get(value),
                        )

                # update membership number
                if not membership.member_number:
                    membership.member_number = AppEntry.objects.count() + 1000
                    membership.save()

                # add user to group
                membership.membership_type.group.add_user(membership.user)

                added.append(membership)
            else:
                skipped.append(membership)

        return render_to_response(template_name, {
            'memberships': memberships,
            'added': added,
            'skipped': skipped,
            'datetime': datetime,
        }, context_instance=RequestContext(request))


#REPORTS
    
def _membership_joins(from_date):
    return Membership.objects.filter(subscribe_dt__gte=from_date)

@staff_member_required
def membership_join_report(request):
    now = datetime.now()
    mems = Membership.objects.all()
    mem_type = ''
    mem_stat = ''
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['membership_type']:
                mem_type = form.cleaned_data['membership_type']
                mems = mems.filter(membership_type = form.cleaned_data['membership_type'])
            if form.cleaned_data['membership_status']:
                mem_stat = form.cleaned_data['membership_status']
                if form.cleaned_data['membership_status'] == 'ACTIVE':
                    mems = mems.filter(expire_dt__gte = now, subscribe_dt__lte = now)
                else:
                    mems = mems.exclude(expire_dt__gte = now, subscribe_dt__lte = now)
    else:
        form = ReportForm()
    mems30days = mems.filter(subscribe_dt__gte = now-timedelta(days=30))
    mems60days = mems.filter(subscribe_dt__gte = now-timedelta(days=60))
    mems90days = mems.filter(subscribe_dt__gte = now-timedelta(days=90))
    return render_to_response(
                'reports/membership_joins.html', {
                    'mems30days': mems30days,
                    'mems60days': mems60days,
                    'mems90days': mems90days,
                    'form': form,
                    'mem_type': mem_type,
                    'mem_stat': mem_stat,
                },
                context_instance=RequestContext(request))
    
@staff_member_required
def membership_export(request):
    #if not is_admin(request.user):raise Http403   # admin only page
    
    template_name = 'memberships/export.html'
    form = ExportForm(request.POST or None, user=request.user)
    
    if request.method == 'POST':
        if form.is_valid():
            app = form.cleaned_data['app']
            
            filename = "memberships_%d_export.csv" % app.id
            
            fields = AppField.objects.filter(app=app).exclude(field_type__in=('section_break', 
                                                               'page_break')).order_by('position')
            label_list = [field.label for field in fields]
            extra_field_labels = ['Subscribe Date', 'Expiration Date', 'Status', 'Status Detail']
            extra_field_names = ['subscribe_dt', 'expire_dt', 'status', 'status_detail']
            
            label_list.extend(extra_field_labels)
            label_list.append('\n')
            
            data_row_list = []
            memberships = Membership.objects.filter(ma=app)
            for memb in memberships:
                data_row = []
                field_entry_d = memb.entry_items
                print field_entry_d
                for field in fields:
                    field_name = slugify(field.label).replace('-','_')
                    value = ''
                    
                    if field.field_type in ['first-name', 'last-name', 'email', 
                                            'membership-type', 'payment-method',
                                            'corporate_membership_id']:
                        if field.field_type == 'first-name':
                            value = memb.user.first_name
                        elif field.field_type == 'last-name':
                            value = memb.user.last_name
                        elif field.field_type == 'email':
                            value = memb.user.email
                        elif field.field_type == 'membership-type':
                            value = memb.membership_type.name
                        elif field.field_type == 'payment-method':
                            if memb.payment_method:
                                value = memb.payment_method.human_name
                        elif field.field_type == 'corporate_membership_id':
                            value = memb.corporate_membership_id
                    
                    if field_entry_d.has_key(field_name):
                        value = field_entry_d[field_name]
                        
                    if value == None:
                        value = ''
                    value_type = type(value)
                    if (value_type is bool) or (value_type is long) or (value_type is int):
                        value = str(value)
                    if (value_type is unicode) or (value_type is str):
                        value = value.replace(',', ' ')
                    data_row.append(value)
                
                for field in extra_field_names:
                    value = ''
                    
                    exec('value=memb.%s' % field)
                    if field == 'expire_dt' and (not memb.expire_dt):
                        value = 'never expire'
                    value_type = type(value)
                    if value_type is bool or value_type is long or value_type is int:
                        value = str(value)
                    data_row.append(value)
                    
                data_row.append('\n')
                data_row_list.append(data_row)
                
            return render_excel(filename, label_list, data_row_list, '.csv')
                    
    return render_to_response(template_name, {
            'form':form
            }, context_instance=RequestContext(request))

@staff_member_required
def membership_join_report_pdf(request):
    now = datetime.now()
    days = request.GET.get('days', 30)
    mem_type = request.GET.get('mem_type', None)
    mem_stat = request.GET.get('mem_stat', None)
    mems = Membership.objects.all()
    if mem_type:
        mems = mems.filter(membership_type=mem_type)
    if mem_stat:
        if mem_stat == 'ACTIVE':
            mems = mems.filter(expire_dt__gte = now, subscribe_dt__lte = now)
        else:
            mems = mems.exclude(expire_dt__gte = now, subscribe_dt__lte = now)
    mems = mems.filter(subscribe_dt__gte = now-timedelta(days=int(days)))
    report = ReportNewMems(queryset = mems)
    resp = HttpResponse(mimetype='application/pdf')
    report.generate_by(PDFGenerator, filename=resp)
    return resp