from rss.feedsmanager import SubFeed
from haystack.query import SearchQuerySet

from site_settings.utils import get_setting
from articles.models import Article

class LatestEntriesFeed(SubFeed):
    title =  '%s Latest Articles' % get_setting('site','global','sitedisplayname')
    link =  "/articles/"
    description =  "Latest Articles by %s" % get_setting('site','global','sitedisplayname')

    def items(self):
        print "Calling items on LatestEntiesFeed"
        sqs = SearchQuerySet().filter(can_syndicate=True).models(Article).order_by('-create_dt')[:20]
        return [sq.object for sq in sqs]

    def item_title(self, item):
        return item.headline

    def item_description(self, item):
        return item.body

    def item_link(self, item):
        return item.get_absolute_url()
