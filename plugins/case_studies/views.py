from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.core.urlresolvers import reverse

from base.http import Http403
from perms.utils import has_perm
from perms.utils import is_admin
from event_logs.models import EventLog

from models import CaseStudy, Service, Technology

def index(request, slug=None, template_name="case_studies/view.html"):
    if not slug: return HttpResponseRedirect(reverse('case_study.search'))
    case_study = get_object_or_404(CaseStudy, slug=slug)

    # non-admin can not view the non-active content
    # status=0 has been taken care of in the has_perm function
    if (case_study.status_detail).lower() <> 'active' and (not is_admin(request.user)):
        raise Http403

    if has_perm(request.user, 'case_studies.view_casestudy', case_study):
        log_defaults = {
            'event_id' : 1000500,
            'event_data': '%s (%d) viewed by %s' % (case_study._meta.object_name, case_study.pk, request.user),
            'description': '%s viewed' % case_study._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': case_study,
        }
        EventLog.objects.log(**log_defaults)
        return render_to_response(template_name, {'case_study': case_study},
            context_instance=RequestContext(request))
    else:
        raise Http403

def search(request, template_name="case_studies/search.html"):
    query = request.GET.get('q', None)
    case_studies = CaseStudy.objects.search(query, user=request.user)
    case_studies = case_studies.order_by('-create_dt')
    
    log_defaults = {
        'event_id' : 1000400,
        'event_data': '%s searched by %s' % ('Case Study', request.user),
        'description': '%s searched' % 'Case Study',
        'user': request.user,
        'request': request,
        'source': 'case_studies'
    }
    EventLog.objects.log(**log_defaults)

    return render_to_response(template_name, {'case_studies': case_studies},
        context_instance=RequestContext(request))        
def service(request, id, template_name="case_studies/search.html"):
    "List of case studies by service"
    service = get_object_or_404(Service, pk=id)
    query = '"service:%s"' % service

    case_studies = CaseStudy.objects.search(query, user=request.user)

    return render_to_response(template_name, {'service':service, 'case_studies': case_studies}, 
        context_instance=RequestContext(request))
        
def technology(request, id, template_name="case_studies/search.html"):
    "List of case studies by technology"
    technology = get_object_or_404(Technology, pk=id)
    query = '"technology:%s"' % technology

    case_studies = CaseStudy.objects.search(query, user=request.user)

    return render_to_response(template_name, {'technology':technology, 'case_studies': case_studies}, 
        context_instance=RequestContext(request))