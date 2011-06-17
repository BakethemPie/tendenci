from haystack import indexes
from haystack import site
from user_groups.models import Group
from perms.indexes import TendenciBaseSearchIndex


class GroupIndex(TendenciBaseSearchIndex):
    name = indexes.CharField(model_attr='name')
    label = indexes.CharField(model_attr='label')
    type = indexes.CharField(model_attr='type')
    description = indexes.CharField(model_attr='description')

site.register(Group, GroupIndex)
