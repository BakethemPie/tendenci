from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import iri_to_uri
from django.utils.text import truncate_words
from django.utils.html import strip_tags
from django.core.urlresolvers import reverse
from django.conf import settings

from event_logs.models import EventLog
from perms.models import ObjectPermission
from models import CaseStudy, Service, Technology, Image
from forms import CaseStudyForm, FileForm

class FileAdmin(admin.StackedInline):
    fieldsets = (
        (None, {'fields': (
            'file',
            'description',
        )},),
    )
    model = Image
    form = FileForm


class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ['view_on_site', 'client', 'slug', 'overview_parsed', 'create_dt']
    list_filter = ['create_dt']
    search_fields = ['client','overview', 'execution', 'results']
    ordering = ('-create_dt',)
    prepopulated_fields = {'slug': ['client']}
    fieldsets = (
        (None, {'fields': (
            'client',
            'slug',
            'url',
            'overview',
            'execution',
            'services',
            'technologies',
            'results',
            'tags'
        )}),
        ('Administrative', {'fields': (
            'allow_anonymous_view','user_perms','group_perms','status','status_detail' )}),
    )
    form = CaseStudyForm
    inlines = (FileAdmin,)
#    change_form_template = 'case_studies/admin/change_form.html'

    def view_on_site(self, obj):
        link_icon = '%s/images/icons/external_16x16.png' % settings.STATIC_URL
        link = '<a href="%s" title="%s"><img src="%s" /></a>' % (
            reverse('case_study.view', args=[obj.slug]),
            obj.client,
            link_icon,
        )
        return link
    view_on_site.allow_tags = True
    view_on_site.short_description = 'view'

    def overview_parsed(self, obj):
        overview = strip_tags(obj.overview)
        overview = truncate_words(overview, 50)
        return overview
    overview_parsed.short_description = 'overview'


    def log_deletion(self, request, object, object_repr):
        super(CaseStudyAdmin, self).log_deletion(request, object, object_repr)
        log_defaults = {
            'event_id' : 1000300,
            'event_data': '%s (%d) deleted by %s' % (object._meta.object_name,
                                                    object.pk, request.user),
            'description': '%s deleted' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        # EventLog.objects.log(**log_defaults)

    def log_change(self, request, object, message):
        super(CaseStudyAdmin, self).log_change(request, object, message)
        log_defaults = {
            'event_id' : 1000200,
            'event_data': '%s (%d) edited by %s' % (object._meta.object_name,
                                                    object.pk, request.user),
            'description': '%s edited' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        # EventLog.objects.log(**log_defaults)

    def log_addition(self, request, object):
        super(CaseStudyAdmin, self).log_addition(request, object)
        log_defaults = {
            'event_id' : 1000100,
            'event_data': '%s (%d) added by %s' % (object._meta.object_name,
                                                   object.pk, request.user),
            'description': '%s added' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        # EventLog.objects.log(**log_defaults)

    def save_model(self, request, object, form, change):
        instance = form.save(commit=False)
        add = not change

        # set up user permission
        instance.allow_user_view, instance.allow_user_edit = form.cleaned_data['user_perms']

        if add:
            instance.creator = request.user
            instance.creator_username = request.user.username
            instance.owner = request.user
            instance.owner_username = request.user.username

        # save the object
        instance.save()
        form.save_m2m()

        # permissions
        if add:
            # assign permissions for selected groups
            ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], instance)
            # assign creator permissions
            ObjectPermission.objects.assign(instance.creator, instance)
        else:
            # assign permissions
            ObjectPermission.objects.remove_all(instance)
            ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], instance)
            ObjectPermission.objects.assign(instance.creator, instance)

        return instance

    def save_formset(self, request, form, formset, change):

        from pprint import pprint

        for f in formset.forms:
            image = f.save(commit=False)
            if image.file:
                image.case_study = form.save()
                image.content_type = ContentType.objects.get_for_model(image.case_study)
                image.object_id = image.case_study.pk
                image.creator = request.user
                image.owner = request.user
                image.save()

        formset.save()


    def change_view(self, request, object_id, extra_context=None):
        result = super(CaseStudyAdmin, self).change_view(request, object_id, extra_context)

        if not request.POST.has_key('_addanother') and not request.POST.has_key('_continue') and request.GET.has_key('next'):
            result['Location'] = iri_to_uri("%s") % request.GET.get('next')
        return result

admin.site.register(CaseStudy, CaseStudyAdmin)
admin.site.register(Service)
admin.site.register(Technology)
admin.site.register(Image)
