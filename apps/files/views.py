import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseServerError
from django.core.urlresolvers import reverse

import simplejson as json
from base.http import Http403
from files.models import File
from files.forms import FileForm
from perms.models import ObjectPermission
from event_logs.models import EventLog

def index(request, id=None, download='', template_name="files/view.html"):
    if not id: return HttpResponseRedirect(reverse('file.search'))
    file = get_object_or_404(File, pk=id)

    # check permission
    if not request.user.has_perm('files.view_file', file):
        raise Http403

    try: data = file.file.read()
    except: raise Http404

    if file.mime_type():
        response = HttpResponse(data, mimetype=file.mime_type())
    else: raise Http404

    if download: download = 'attachment;'
    response['Content-Disposition'] = '%s filename=%s'% (download, file.file.name)

    return response

def search(request, template_name="files/search.html"):
    query = request.GET.get('q', None)
    files = File.objects.search(query)

    return render_to_response(template_name, {'files':files}, 
        context_instance=RequestContext(request))

def print_view(request, id, template_name="files/print-view.html"):
    file = get_object_or_404(File, pk=id)

    # check permission
    if not request.user.has_perm('files.view_file', file):
        raise Http403

    return render_to_response(template_name, {'file': file}, 
        context_instance=RequestContext(request))
    
@login_required
def edit(request, id, form_class=FileForm, template_name="files/edit.html"):
    file = get_object_or_404(File, pk=id)

    # check permission
    if not request.user.has_perm('files.change_file', file):  
        raise Http403

    if request.method == "POST":

        form = form_class(request.user, request.POST, request.FILES, instance=file)

        if form.is_valid():
            file = form.save()

            log_defaults = {
                'event_id' : 182000,
                'event_data': '%s (%d) edited by %s' % (file._meta.object_name, file.pk, request.user),
                'description': '%s edited' % file._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': file,
            }
            EventLog.objects.log(**log_defaults)
                
            # remove all permissions on the object
            ObjectPermission.objects.remove_all(file)            
    
            # assign creator permissions
            ObjectPermission.objects.assign(file.creator, file) 
                                                          
            return HttpResponseRedirect(reverse('file', args=[file.pk]))             
    else:
        form = form_class(request.user, instance=file)
    
    return render_to_response(template_name, {'file': file, 'form':form}, 
        context_instance=RequestContext(request))

@login_required
def add(request, form_class=FileForm, template_name="files/add.html"):

    # check permission
    if not request.user.has_perm('files.add_file'):  
        raise Http403

    if request.method == "POST":
        form = form_class(request.user, request.POST, request.FILES)
        if form.is_valid():
            file = form.save(commit=False)
            
            # set up the user information
            file.creator = request.user
            file.creator_username = request.user.username
            file.owner = request.user
            file.owner_username = request.user.username        
            file.save()

            log_defaults = {
                'event_id' : 181000,
                'event_data': '%s (%d) added by %s' % (file._meta.object_name, file.pk, request.user),
                'description': '%s added' % file._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': file,
            }
            EventLog.objects.log(**log_defaults)


#            # assign permissions for selected users
#            user_perms = form.cleaned_data['user_perms']
#            if user_perms: ObjectPermission.objects.assign(user_perms, file)
            
            # assign creator permissions
            ObjectPermission.objects.assign(file.creator, file) 
            
            return HttpResponseRedirect(reverse('file', args=[file.pk]))
    else:
        form = form_class()
       
    return render_to_response(template_name, {'form':form}, 
        context_instance=RequestContext(request))
    
@login_required
def delete(request, id, template_name="files/delete.html"):
    file = get_object_or_404(File, pk=id)

    # check permission
    if not request.user.has_perm('files.delete_file'): 
        raise Http403

    if request.method == "POST":
        log_defaults = {
            'event_id' : 183000,
            'event_data': '%s (%d) deleted by %s' % (file._meta.object_name, file.pk, request.user),
            'description': '%s deleted' % file._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': file,
        }
        EventLog.objects.log(**log_defaults)

        file.delete()

        if request.POST['ajax']:
            return HttpResponse('Ok')
        else:
            return HttpResponseRedirect(reverse('file.search'))
        

    return render_to_response(template_name, {'file': file}, 
        context_instance=RequestContext(request))


@login_required
def tinymce(request, template_name="media-files/tinymce.html"):
    """
    TinyMCE Insert/Edit images [Window]
    Passes in a list of files associated w/ "this" object
    Examples of "this": Articles, Pages, Releases module
    """
    from django.contrib.contenttypes.models import ContentType
    params = {'app_label': 0, 'model': 0, 'instance_id':0}
    files = File.objects.none() # EmptyQuerySet

    # if all required parameters are in the GET.keys() list
    # difference of 0, negated = True;
    if not set(params.keys()) - set(request.GET.keys()):        
        for item in params: params[item] = request.GET[item]
        try: # get content type
            contenttype = ContentType.objects.get(app_label=params['app_label'], model=params['model'])

            print 'contenttype', contenttype
            print 'instance id', params['instance_id']

            if params['instance_id'] == 'undefined':
                params['instance_id'] = 0

            files = File.objects.filter(content_type=contenttype, object_id=params['instance_id'])

            print 'files', files

            for media_file in files:
                file, ext = os.path.splitext(media_file.file.url)
                media_file.file.url_thumbnail = '%s_thumbnail%s' % (file, ext)
                media_file.file.url_medium = '%s_medium%s' % (file, ext)
                media_file.file.url_large = '%s_large%s' % (file, ext)
        except ContentType.DoesNotExist: raise Http404

    return render_to_response(template_name, {"media": files}, context_instance=RequestContext(request))


def swfupload(request):

    from django.contrib.contenttypes.models import ContentType
    import re

    if request.method == "POST":

        form = FileForm(request.user, request.POST, request.FILES)

        if not form.is_valid():
            return HttpResponseServerError(
                str(form._errors), mimetype="text/plain")

        app_label = request.POST['storme_app_label']
        model = unicode(request.POST['storme_model']).lower()
        object_id = request.POST['storme_instance_id']

        try:
            file = form.save(commit=False)
            file.name = re.sub(r'[^a-zA-Z0-9._]+', '-', request.FILES['file'].name)
            file.content_type = ContentType.objects.get(app_label=app_label, model=model)
            file.object_id = object_id
            file.owner = request.user
            file.creator = request.user
            file.save()
        except Exception, e:
            print e

        d = {
            "id" : file.id,
            "name" : file.name,
            "url" : file.file.url,
        }

        return HttpResponse(json.dumps([d]), mimetype="text/plain")

@login_required
def tinymce_upload_template(request, id, template_name="files/templates/tinymce_upload.html"):
    file = get_object_or_404(File, pk=id)
    return render_to_response(template_name, {'file': file}, 
        context_instance=RequestContext(request))
