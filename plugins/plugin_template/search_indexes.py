from haystack import indexes
from haystack import site

from perms.indexes import TendenciBaseSearchIndex
from S_P_LOW.models import S_S_CAP

class S_S_CAPIndex(TendenciBaseSearchIndex):

    # RSS fields
    can_syndicate = indexes.BooleanField()
    order = indexes.DateTimeField()

    def prepare_can_syndicate(self, obj):
        return obj.allow_anonymous_view and obj.status == 1 \
        and obj.status_detail == 'active'

    def prepare_syndicate_order(self, obj):
        return obj.update_dt

site.register(S_S_CAP, S_S_CAPIndex)
