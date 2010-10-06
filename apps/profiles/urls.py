from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('profiles.views',                  
    url(r'^$','index', name="profile.index"),
    #url(r'^(?P<id>\d+)/$',     'index', name="profile"),
    url(r'^search/$',   'search', name="profile.search"),
    url(r'^add/$',  'add', name="profile.add"),
    url(r'^edit/(?P<id>\d+)/$',     'edit', name="profile.edit"),
    url(r'^edit_perms/(?P<id>\d+)/$',   'edit_user_perms', name="profile.edit_perms"),
    # url(r'^edit_groups/(?P<id>\d+)/$',  'edit_user_groups', name="profile.edit_groups"),
    url(r'^avatar/(?P<id>\d+)/$',  'change_avatar', name="profile.change_avatar"),
    url(r'^delete/(?P<id>\d+)/$',   'delete', name="profile.delete"),
    url(r'^(?P<username>[+-.\w@]+)/$','index', name='profile'),
)
