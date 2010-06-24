from django.conf.urls.defaults import patterns, url
from news.feeds import LatestEntriesFeed

urlpatterns = patterns('',                  
    url(r'^$', 'news.views.index', name="news"),
    url(r'^(?P<id>\d+)/$', 'news.views.index', name="news.view"),
    url(r'^search/$', 'news.views.search', name="news.search"),
    url(r'^print-view/(?P<id>\d+)/$', 'news.views.print_view', name="news.print_view"),
    url(r'^add/$', 'news.views.add', name="news.add"),
    url(r'^edit/(?P<id>\d+)/$', 'news.views.edit', name="news.edit"),
    url(r'^edit/meta/(?P<id>\d+)/$', 'views.edit_meta', name="news.edit.meta"),
    url(r'^delete/(?P<id>\d+)/$', 'news.views.delete', name="news.delete"),
    url(r'^feed/$', LatestEntriesFeed(), name='news.feed'),
)