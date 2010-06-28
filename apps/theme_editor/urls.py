from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('',    
    url(r'^$', 'theme_editor.views.edit_file', name="theme_editor"),
    url(r'^get-version/(\d+)/$', 'theme_editor.views.get_version', name="theme_editor_get_version"),
)