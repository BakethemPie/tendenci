from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template, redirect_to

# Django admin
from django.contrib import admin
admin.autodiscover()

# authority permissions
import authority
authority.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {"template": "homepage.html",}, name="home"),
    
    #Reports:
    (r'^reports/', include('reports.urls')),
    url(r'^event-logs/reports/summary/$', 'event_logs.views.event_summary_report', name='reports-events-summary'),
    url(r'^event-logs/reports/summary/([^/]+)/$', 'event_logs.views.event_source_summary_report', name='reports-events-source'),
    url(r'^users/reports/users-activity-top10/$', 'profiles.views.user_activity_report', name='reports-user-activity'),
    url(r'^users/reports/active-logins/$', 'profiles.views.user_access_report', name='reports-user-access'),
    url(r'^users/reports/admin/$', 'profiles.views.admin_users_report', name='reports-admin-users'),
    url(r'^users/reports/users-added/$', 'user_groups.views.users_added_report', {'kind': 'added'}, name='reports-user-added'),
    url(r'^users/reports/contacts-referral/$', 'user_groups.views.users_added_report', {'kind': 'referral'}, name='reports-contacts-referral'),
    url(r'^articles/reports/rank/$', 'articles.views.articles_report', name='reports-articles'),

    (r'^notifications/', include('notification.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^base/', include('base.urls')),
    (r'^avatar/', include('avatar.urls')),
    (r'^dashboard/', include('dashboard.urls')),
    (r'^categories/', include('categories.urls')),
    (r'^articles/', include('articles.urls')),
    (r'^entities/', include('entities.urls')),
    (r'^locations/', include('locations.urls')),
    (r'^pages/', include('pages.urls')),
    (r'^users/', include('profiles.urls')),
    (r'^photos/', include('photos.urls')),
    (r'^forms/', include('forms_builder.forms.urls')),
    (r'^events/', include('events.urls')),
    (r'^profiles/', include('profiles.urls')),
    (r'^groups/', include('user_groups.urls')),
    (r'^stories/', include('stories.urls')),
    (r'^invoices/', include('invoices.urls')),
    (r'^py/', include('make_payments.urls')),
    (r'^payments/', include('payments.urls')),
    (r'^accountings/', include('accountings.urls')),
    (r'^emails/', include('emails.urls')),
    (r'^newsletters/', include('newsletters.urls')),
    (r'^actions/', include('actions.urls')),
    (r'^rss/', include('rss.urls')),
    (r'^imports/', include('imports.urls')),
    (r'^news/', include('news.urls')),
    (r'^settings/', include('site_settings.urls')),
    (r'^files/', include('files.urls')),
    (r'^contacts/', include('contacts.urls')),
    (r'^accounts/', include('accounts.urls')),
    (r'^search/', include('search.urls')),
    (r'^event-logs/', include('event_logs.urls')),
    (r'^contributions/', include('contributions.urls')),
    (r'^theme-editor/', include('theme_editor.urls')),
    (r'^jobs/', include('jobs.urls')),
    (r'^directories/', include('directories.urls')),
    (r'^contact/', include('form_builder.urls')),
    (r'^sitemap.xml', include('sitemaps.urls')),
    (r'^helpfiles/', include('helpfiles.urls')),
    # third party (inside environment)
    (r'^tinymce/', include('tinymce.urls')),
    (r'^captcha/', include('captcha.urls')),
    (r'^redirects/', include('redirects.urls')),

    url(r'^sitemap/$', direct_to_template, {"template": "site_map.html",}, name="site_map"),
    url(r'^robots.txt', direct_to_template, {"template": "robots.txt",}, name="robots"),
    
    # lEGACY REDIRECTS
    # rss redirect
    url(r'^en/rss/$', redirect_to, {'url':'/rss'}),
)

handler500 = 'base.views.custom_error'

# Local url patterns for development
try:
    from local_urls import MEDIA_PATTERNS
    urlpatterns += MEDIA_PATTERNS
except ImportError:
    pass

# tack on the pages pattern at the very end so let custom and software patterns
# happen first
pattern_pages = patterns('',
    # page view  
    url(r'^(?P<slug>[\w\-\/]+)/$', 'pages.views.index', name="page"),              
)
urlpatterns += pattern_pages