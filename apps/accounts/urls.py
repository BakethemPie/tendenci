from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

from registration.views import activate


from profiles.views import password_change, password_change_done

from accounts.forms import RegistrationCustomForm
from accounts.views import register

urlpatterns = patterns('',
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           {'template_name': 'accounts/activate.html'},
                           name='registration_activate'),
                       url(r'^login/$',
                           'accounts.views.login',
                           {'template_name': 'accounts/login.html'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'accounts/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/(?P<id>\d+)/$',
                           password_change,
                           name='auth_password_change'),
                       url(r'^password/change/done/(?P<id>\d+)/$',
                           password_change_done,
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           auth_views.password_reset,
                           name='auth_password_reset'),
                       url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           auth_views.password_reset_confirm,
                           name='auth_password_reset_confirm'),
                       url(r'^password/reset/complete/$',
                           auth_views.password_reset_complete,
                           name='auth_password_reset_complete'),
                       url(r'^password/reset/done/$',
                           auth_views.password_reset_done,
                           name='auth_password_reset_done'),
                       url(r'^register/$',
                           register, {'form_class' : RegistrationCustomForm, 'template_name': 'accounts/registration_form.html'},
                           name='registration_register'),
                       url(r'^register/complete/$',
                           direct_to_template,
                           {'template': 'accounts/registration_complete.html'},
                           name='registration_complete'),
                       )
