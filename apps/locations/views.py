from datetime import datetime
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages

from base.http import Http403
from site_settings.utils import get_setting
from event_logs.models import EventLog
from perms.utils import (is_admin, has_perm, has_view_perm,
    update_perms_and_save, get_query_filters)
from theme.shortcuts import themed_response as render_to_response

from locations.models import Location, LocationImport
from locations.forms import LocationForm
from locations.utils import get_coordinates
from locations.importer.forms import UploadForm, ImportMapForm
from locations.importer.utils import is_import_valid, parse_locs_from_csv
from locations.importer.tasks import ImportLocationsTask
from files.models import File
from djcelery.models import TaskMeta


def index(request, id=None, template_name="locations/view.html"):
    if not id: return HttpResponseRedirect(reverse('locations'))
    location = get_object_or_404(Location, pk=id)
    
    if has_view_perm(request.user,'locations.view_location',location):
        log_defaults = {
            'event_id' : 835000,
            'event_data': '%s (%d) viewed by %s' % (location._meta.object_name, location.pk, request.user),
            'description': '%s viewed' % location._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': location,
        }
        EventLog.objects.log(**log_defaults)
        return render_to_response(template_name, {'location': location}, 
            context_instance=RequestContext(request))
    else:
        raise Http403


def search(request, template_name="locations/search.html"):
    query = request.GET.get('q', None)

    if get_setting('site', 'global', 'searchindex') and query:
        locations = Location.objects.search(query, user=request.user)
    else:
        filters = get_query_filters(request.user, 'locations.view_location')
        locations = Location.objects.filter(filters).distinct()
        if not request.user.is_anonymous():
            locations = locations.select_related()

    locations = locations.order_by('-create_dt')

    log_defaults = {
        'event_id' : 834000,
        'event_data': '%s listed by %s' % ('Location', request.user),
        'description': '%s listed' % 'Location',
        'user': request.user,
        'request': request,
        'source': 'locations'
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(template_name, {'locations':locations}, 
        context_instance=RequestContext(request))


def search_redirect(request):
    return HttpResponseRedirect(reverse('locations'))


def nearest(request, template_name="locations/nearest.html"):
    locations = []
    lat, lng = None, None
    query = request.GET.get('q')
    filters = get_query_filters(request.user, 'locations.view_location')

    if query:
        lat, lng = get_coordinates(address=query)

    all_locations = Location.objects.filter(filters).distinct()
    if not request.user.is_anonymous():
        all_locations = all_locations.select_related()

    if all((lat,lng)):
        for location in all_locations:
            location.distance = location.get_distance2(lat, lng)
            if location.distance != None:
                locations.append(location)
            locations.sort(key=lambda x: x.distance)

    log_defaults = {
        'event_id' : 834100,
        'event_data': '%s nearest to %s' % ('Location', request.user),
        'description': '%s nearest' % 'Location',
        'user': request.user,
        'request': request,
        'source': 'locations'
    }
    EventLog.objects.log(**log_defaults)

    return render_to_response(template_name, {
        'locations':locations,
        'origin': {'lat':lat,'lng':lng},
        }, context_instance=RequestContext(request))


def print_view(request, id, template_name="locations/print-view.html"):
    location = get_object_or_404(Location, pk=id)    

    if has_view_perm(request.user,'locations.view_location',location):
        log_defaults = {
            'event_id' : 835000,
            'event_data': '%s (%d) viewed by %s' % (location._meta.object_name, location.pk, request.user),
            'description': '%s viewed' % location._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': location,
        }
        EventLog.objects.log(**log_defaults)

        return render_to_response(template_name, {'location': location}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
    
@login_required
def edit(request, id, form_class=LocationForm, template_name="locations/edit.html"):
    location = get_object_or_404(Location, pk=id)

    if has_perm(request.user,'locations.change_location',location):    
        if request.method == "POST":
            form = form_class(request.POST, instance=location, user=request.user)
            if form.is_valid():
                location = form.save(commit=False)

                # update all permissions and save the model
                location = update_perms_and_save(request, form, location)

                log_defaults = {
                    'event_id' : 832000,
                    'event_data': '%s (%d) edited by %s' % (location._meta.object_name, location.pk, request.user),
                    'description': '%s edited' % location._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': location,
                }
                EventLog.objects.log(**log_defaults)               
                
                messages.add_message(request, messages.SUCCESS, 'Successfully updated %s' % location)
                                                              
                return HttpResponseRedirect(reverse('location', args=[location.pk]))             
        else:
            form = form_class(instance=location, user=request.user)

        return render_to_response(template_name, {'location': location, 'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def add(request, form_class=LocationForm, template_name="locations/add.html"):
    if has_perm(request.user,'locations.add_location'):
        if request.method == "POST":
            form = form_class(request.POST, user=request.user)
            if form.is_valid():           
                location = form.save(commit=False)

                # update all permissions and save the model
                location = update_perms_and_save(request, form, location)
 
                log_defaults = {
                    'event_id' : 831000,
                    'event_data': '%s (%d) added by %s' % (location._meta.object_name, location.pk, request.user),
                    'description': '%s added' % location._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': location,
                }
                EventLog.objects.log(**log_defaults)
                
                messages.add_message(request, messages.SUCCESS, 'Successfully added %s' % location)
                
                return HttpResponseRedirect(reverse('location', args=[location.pk]))
        else:
            form = form_class(user=request.user)
           
        return render_to_response(template_name, {'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
    
@login_required
def delete(request, id, template_name="locations/delete.html"):
    location = get_object_or_404(Location, pk=id)

    if has_perm(request.user,'locations.delete_location'):   
        if request.method == "POST":
            log_defaults = {
                'event_id' : 833000,
                'event_data': '%s (%d) deleted by %s' % (location._meta.object_name, location.pk, request.user),
                'description': '%s deleted' % location._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': location,
            }
            
            EventLog.objects.log(**log_defaults)
            messages.add_message(request, messages.SUCCESS, 'Successfully deleted %s' % location)
            location.delete()
                
            return HttpResponseRedirect(reverse('location.search'))
    
        return render_to_response(template_name, {'location': location}, 
            context_instance=RequestContext(request))
    else:
        raise Http403


@login_required
def locations_import_upload(request, template_name='locations/import-upload-file.html'):
    """
    This is the upload view for the location imports.
    This will upload the location import file and then redirect the user
    to the import mapping/preview page of the import file
    """

    if not is_admin(request.user):
        raise Http403

    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            
            locport = LocationImport.objects.create(creator=request.user)
            csv = File.objects.save_files_for_instance(request, locport)[0]
            file_path = os.path.join(settings.MEDIA_ROOT, csv.file.name)
            import_valid, import_errs = is_import_valid(file_path)

            if not import_valid:
                for err in import_errs:
                    messages.add_message(request, messages.ERROR, err)
                locport.delete()
                return redirect('locations_import_upload_file')

            return redirect('locations_import_preview', locport.id)
    else:
        form = UploadForm()

    return render_to_response(template_name, {
            'form': form,
            'now': datetime.now(),
        }, context_instance=RequestContext(request))


@login_required
def locations_import_preview(request, id, template_name='locations/import-map-fields.html'):
    """
    This will generate a form based on the uploaded CSV for field mapping.
    A preview will be generated based on the mapping given.
    """
    if not is_admin(request.user):
        raise Http403
    
    locport = get_object_or_404(LocationImport, pk=id)
    
    if request.method == 'POST':
        form = ImportMapForm(request.POST, locport=locport)

        if form.is_valid():
            # Show the user a preview based on the mapping
            cleaned_data = form.cleaned_data
            file_path = os.path.join(settings.MEDIA_ROOT, locport.get_file().file.name)
            locations, stats = parse_locs_from_csv(file_path, cleaned_data)
            
            # return the form to use it for the confirm view
            template_name = 'locations/import-preview.html'
            return render_to_response(template_name, {
                'locations': locations,
                'stats': stats,
                'locport': locport,
                'form': form,
                'now': datetime.now(),
            }, context_instance=RequestContext(request))

    else:
        form = ImportMapForm(locport=locport)

    return render_to_response(template_name, {
        'form': form,
        'locport': locport,
        'now': datetime.now(),
        }, context_instance=RequestContext(request))


@login_required
def locations_import_confirm(request, id, template_name='locations/import-confirm.html'):
    """
    Confirm the locations import and continue with the process.
    This can only be accessed via a hidden post form from the preview page.
    That will hold the original mappings selected by the user.
    """
    if not is_admin(request.user):
        raise Http403

    locport = get_object_or_404(LocationImport, pk=id)
    
    if request.method == "POST":
        form = ImportMapForm(request.POST, locport=locport)

        if form.is_valid():
            print "form valid"
            cleaned_data = form.cleaned_data
            file_path = os.path.join(settings.MEDIA_ROOT, locport.get_file().file.name)
            print "file path" + str(file_path)

            if not settings.CELERY_IS_ACTIVE:
                print "celery not active"
                # if celery server is not present 
                # evaluate the result and render the results page
                result = ImportLocationsTask()
                print result
                locations, stats = result.run(request.user, file_path, cleaned_data)
                return render_to_response(template_name, {
                    'locations': locations,
                    'stats': stats,
                    'now': datetime.now(),
                }, context_instance=RequestContext(request))
            else:
                print "celery active"
                result = ImportLocationsTask.delay(request.user, file_path, cleaned_data)
                print result

            print "confirm finished, redirecting"
            return redirect('locations_import_status', result.task_id)
    else:
        return redirect('locations_import_preview', locport.id)


@login_required
def locations_import_status(request, task_id, template_name='locations/import-confirm.html'):
    """
    Checks if a location import is completed.
    """
    if not is_admin(request.user):
        raise Http403

    try:
        task = TaskMeta.objects.get(task_id=task_id)
    except TaskMeta.DoesNotExist:
        #tasks database entries are not created at once.
        task = None
    
    if task and task.status == "SUCCESS":

        locations, stats = task.result
        
        return render_to_response(template_name, {
            'locations': locations,
            'stats':stats,
            'now': datetime.now(),
        }, context_instance=RequestContext(request))
    else:
        return render_to_response('memberships/import-status.html', {
            'task': task,
            'now': datetime.now(),
        }, context_instance=RequestContext(request))

