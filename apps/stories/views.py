import os.path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages

from base.http import Http403
from stories.models import Story
from stories.forms import StoryForm, UploadStoryImageForm
from perms.models import ObjectPermission
from perms.utils import has_perm
from event_logs.models import EventLog


def index(request, id=None, template_name="stories/view.html"):
    if not id: return HttpResponseRedirect(reverse('story.search'))
    story = get_object_or_404(Story, pk=id)
    
    if not has_perm(request.user,'stories.view_story', story):
        raise Http403

    log_defaults = {
        'event_id' : 1060500,
        'event_data': '%s (%d) viewed by %s' % (story._meta.object_name, story.pk, request.user),
        'description': '%s viewed' % story._meta.object_name,
        'user': request.user,
        'request': request,
        'instance': story,
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(template_name, {'story': story}, 
        context_instance=RequestContext(request))
    
    
def search(request, template_name="stories/search.html"):
    query = request.GET.get('q', None)
    stories = Story.objects.search(query, user=request.user)
    stories = stories.order_by('-create_dt')

    log_defaults = {
        'event_id' : 1060400,
        'event_data': '%s searched by %s' % ('Story', request.user),
        'description': '%s searched' % 'Story',
        'user': request.user,
        'request': request,
        'source': 'stories'
    }
    EventLog.objects.log(**log_defaults)
    
    return render_to_response(template_name, {'stories':stories}, 
        context_instance=RequestContext(request))
    
    
@login_required   
def add(request, form_class=StoryForm, template_name="stories/add.html"):
    
    if has_perm(request.user,'stories.add_story'):    
        if request.method == "POST":
            form = form_class(request.POST, request.FILES, user=request.user)
            if form.is_valid():           
                story = form.save(commit=False)
                # set up the user information
                story.creator = request.user
                story.creator_username = request.user.username
                story.owner = request.user
                story.owner_username = request.user.username
    
                # set up user permission
                story.allow_user_view, story.allow_user_edit = form.cleaned_data['user_perms']
    
                story.save() # get pk
    
                # assign permissions for selected groups
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], story)
                # assign creator permissions
                ObjectPermission.objects.assign(story.creator, story) 
    
                story.save() # update search-index w/ permissions
    
                log_defaults = {
                    'event_id' : 1060100,
                    'event_data': '%s (%d) added by %s' % (story._meta.object_name, story.pk, request.user),
                    'description': '%s added' % story._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': story,
                }
                EventLog.objects.log(**log_defaults)
                
                messages.add_message(request, messages.INFO, 'Successfully added %s' % story) 
                
                return HttpResponseRedirect(reverse('story', args=[story.pk]))
            else:
                from pprint import pprint
                pprint(form.errors.items())
        else:
            form = form_class(user=request.user)
    
    return render_to_response(template_name, {'form':form}, 
        context_instance=RequestContext(request))
    
@login_required
def edit(request, id, form_class=StoryForm, template_name="stories/edit.html"):
    story = get_object_or_404(Story, pk=id)

    if has_perm(request.user,'stories.change_story', story):
        if request.method == "POST":
            form = form_class(request.POST, request.FILES,
                              instance=story, user=request.user)
            if form.is_valid():
                story = form.save(commit=False)

                # set up user permission
                story.allow_user_view, story.allow_user_edit = form.cleaned_data['user_perms']
        
                # assign permissions
                ObjectPermission.objects.remove_all(story)
                ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], story)
                ObjectPermission.objects.assign(story.creator, story) 
    
                story.save()
                
                log_defaults = {
                    'event_id' : 1060200,
                    'event_data': '%s (%d) edited by %s' % (story._meta.object_name, story.pk, request.user),
                    'description': '%s edited' % story._meta.object_name,
                    'user': request.user,
                    'request': request,
                    'instance': story,
                }
                EventLog.objects.log(**log_defaults)
                
                messages.add_message(request, messages.INFO, 'Successfully updated %s' % story)
                                                                 
                return HttpResponseRedirect(reverse('story', args=[story.pk]))             
        else:
            form = form_class(instance=story, user=request.user)
    
    return render_to_response(template_name, {'story': story, 'form':form }, 
        context_instance=RequestContext(request))

@login_required
def delete(request, id, template_name="stories/delete.html"):
    story = get_object_or_404(Story, pk=id)

    if has_perm(request.user,'stories.delete_story'):   
        if request.method == "POST":
            log_defaults = {
                'event_id' : 1060300,
                'event_data': '%s (%d) deleted by %s' % (story._meta.object_name, story.pk, request.user),
                'description': '%s deleted' % story._meta.object_name,
                'user': request.user,
                'request': request,
                'instance': story,
            }
            EventLog.objects.log(**log_defaults)
            
            messages.add_message(request, messages.INFO, 'Successfully deleted %s' % story)
            story.delete()
            
            return HttpResponseRedirect(reverse('story.search'))
    
        return render_to_response(template_name, {'story': story}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
 
@login_required   
def upload(request, id, form_class=UploadStoryImageForm, 
                template_name="stories/upload.html"):
    story = get_object_or_404(Story, pk=id)
    # permission check
    if not story.allow_edit_by(request.user): raise Http403
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data['file']
            imagename = data.name
            imagepath = os.path.join(settings.MEDIA_ROOT, 'stories/'+str(story.id))
            if not os.path.isdir(imagepath):
                os.makedirs(imagepath)
            fd = open(imagepath + '/' + imagename, 'wb+')
            for chunk in data.chunks():
                fd.write(chunk)
            fd.close()
            #filelog(mode='wb+', filename=imagename, path=imagepath)
            return HttpResponseRedirect(reverse('story', args=[story.pk]))
    else:
        form = form_class(user=request.user)
    return render_to_response(template_name, {'form':form, 'story': story}, 
            context_instance=RequestContext(request))
    
            
            
            