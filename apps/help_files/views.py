from django.template.context import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse

from base.http import Http403
from event_logs.models import EventLog
from perms.utils import has_perm
from models import Topic, HelpFile, HelpFileMigration
from forms import RequestForm

def index(request, template_name="help_files/index.html"):
    "List all topics and all links"
    
    topics = list(Topic.objects.all())
    m = len(topics)/2
    topics = topics[:m], topics[m:] # two columns
    most_viewed = HelpFile.objects.filter(allow_anonymous_view=True).order_by('-view_totals')[:5]
    featured = HelpFile.objects.filter(is_featured=True, allow_anonymous_view=True)[:5]
    faq = HelpFile.objects.filter(is_faq=True, allow_anonymous_view=True)[:3]

    return render_to_response(template_name, locals(), 
        context_instance=RequestContext(request))

def search(request, template_name="help_files/search.html"):
    """ Help Files Search """
    query = request.GET.get('q', None)
    help_files = HelpFile.objects.search(query, user=request.user)

    log_defaults = {
        'event_id' : 1000400,
        'event_data': '%s searched by %s' % ('Help File', request.user),
        'description': '%s searched' % 'Help File',
        'user': request.user,
        'request': request,
        'source': 'help_files'
    }
    EventLog.objects.log(**log_defaults)

    return render_to_response(template_name, {'help_files':help_files}, 
        context_instance=RequestContext(request))

def topic(request, id, template_name="help_files/topic.html"):
    "List of topic help files"
    topic = get_object_or_404(Topic, pk=id)

    help_files = HelpFile.objects.search(topic=topic, user=request.user)

    return render_to_response(template_name, {'topic':topic, 'help_files':help_files}, 
        context_instance=RequestContext(request))

def details(request, slug, template_name="help_files/details.html"):
    "Help file details"
    help_file = get_object_or_404(HelpFile, slug=slug)
    help_file.view_totals += 1
    help_file.save()

    if has_perm(request.user, 'help_files.view_helpfile', help_file):
        log_defaults = {
            'event_id' : 1000500,
            'event_data': '%s (%d) viewed by %s' % (help_file._meta.object_name, help_file.pk, request.user),
            'description': '%s viewed' % help_file._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': help_file,
        }
        EventLog.objects.log(**log_defaults)
        return render_to_response(template_name, {'help_file': help_file}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def request_new(request, template_name="help_files/request_new.html"):
    "Request new file form"
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, 'Thanks for requesting a new help file!')
            return HttpResponseRedirect(reverse('help_files'))
    else:
        form = RequestForm()
        
    return render_to_response(template_name, {'form': form}, 
        context_instance=RequestContext(request))
    
def redirects(request, id):
    """
        Redirect old Tendenci 4 IDs to new Tendenci 5 slugs
    """
    try:
        help_file_migration = HelpFileMigration.objects.get(t4_id=id)
        try:
            help_file = HelpFile.objects.get(pk=help_file_migration.t5_id)
            return HttpResponsePermanentRedirect(help_file.get_absolute_url())
        except:
            return HttpResponsePermanentRedirect(reverse('help_files'))
    except:
        return HttpResponsePermanentRedirect(reverse('help_files'))

        
    