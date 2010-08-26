from django.utils.html import strip_tags, strip_entities

from haystack import indexes
from haystack import site
from events.models import Event, Registrant
from perms.models import ObjectPermission

class EventIndex(indexes.RealTimeSearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    description = indexes.CharField(model_attr='description')
    start_dt = indexes.DateTimeField(model_attr='start_dt')

    # authority fields
    allow_anonymous_view = indexes.BooleanField(model_attr='allow_anonymous_view')
    allow_user_view = indexes.BooleanField(model_attr='allow_user_view')
    allow_member_view = indexes.BooleanField(model_attr='allow_member_view')
    allow_anonymous_edit = indexes.BooleanField(model_attr='allow_anonymous_edit')
    allow_user_edit = indexes.BooleanField(model_attr='allow_user_edit')
    allow_member_edit = indexes.BooleanField(model_attr='allow_member_edit')
    creator = indexes.CharField(model_attr='creator')
    creator_username = indexes.CharField(model_attr='creator_username')
    owner = indexes.CharField(model_attr='owner')
    owner_username = indexes.CharField(model_attr='owner_username')
    status = indexes.IntegerField(model_attr='status')
    status_detail = indexes.CharField(model_attr='status_detail')

    who_can_view = indexes.CharField()
    can_syndicate = indexes.BooleanField()

    def prepare_who_can_view(self, obj):
        users = ObjectPermission.objects.who_has_perm('events.view_event', obj)
        if not users: users = []
        return ','.join([user.username for user in users])

    def prepare_can_syndicate(self, obj):
        return obj.allow_anonymous_view and obj.status==1 \
                and obj.status_detail=='active'

    def prepare_description(self, obj):
        description = obj.description
        description = strip_tags(description)
        description = strip_entities(description)
        return description


class RegistrantIndex(indexes.RealTimeSearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    event = indexes.CharField(model_attr='registration__event')

    who_can_view = indexes.CharField()

    def prepare_who_can_view(self, obj):
        users = ObjectPermission.objects.who_has_perm('registrants.view_registrant', obj)
        if not users: users = []
        return ','.join([user.username for user in users])
    
site.register(Event, EventIndex)
site.register(Registrant, RegistrantIndex)



