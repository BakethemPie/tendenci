from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('navs',
    url(r'^$', 'views.search', name="navs.search"),
    url(r'^add/$', 'views.add', name="navs.add"),
    url(r'^detail/(?P<id>\d+)/$', 'views.detail', name="navs.detail"),
    url(r'^edit/(?P<id>\d+)/$', 'views.edit', name="navs.edit"),
    url(r'^edit/(?P<id>\d+)/items/$', 'views.edit_items', name="navs.edit_items"),
    url(r'^page-select/$', 'views.page_select', name="navs.page_select"),
)
