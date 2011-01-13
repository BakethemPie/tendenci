from haystack import indexes
from haystack import site

from models import Staff
from perms.models import ObjectPermission

class StaffIndex(indexes.RealTimeSearchIndex):
    text = indexes.CharField(document=True, use_template=True)

    name = indexes.CharField(model_attr='name')
    department = indexes.CharField(model_attr='department', null=True)
    position = indexes.CharField(model_attr='position', null=True)
    start_date = indexes.DateField(model_attr='start_date')

    # base fields
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
    create_dt = indexes.DateTimeField(model_attr='create_dt', null=True)
    update_dt = indexes.DateTimeField(model_attr='update_dt', null=True)

    who_can_view = indexes.CharField()

    def prepare_who_can_view(self, obj):
        users = ObjectPermission.objects.who_has_perm('staff.view_staff', obj)
        user_list = []
        if users:
            for user in users:
                user_list.append(user.username)
            return ','.join(user_list)
        else:
            return ''

site.register(Staff, StaffIndex)
