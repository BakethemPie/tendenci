from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('campaign_monitor',                  
    url(r'^templates/$', 'views.template_index', name="campaign_monitor.template_index"),
    url(r'^templates/add/$', 'views.template_add', name="campaign_monitor.template_add"),
    url(r'^templates/sync/$', 'views.template_sync', name="campaign_monitor.template_sync"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/page.html$', 'views.template_html', name="campaign_monitor.template_html"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/render/$', 'views.template_render', name="campaign_monitor.template_render"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/text/$', 'views.template_text', name="campaign_monitor.template_text"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/edit/$', 'views.template_edit', name="campaign_monitor.template_edit"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/delete/$', 'views.template_delete', name="campaign_monitor.template_delete"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/update/$', 'views.template_update', name="campaign_monitor.template_update"),
    url(r'^templates/(?P<template_id>[\w\-\/]+)/$', 'views.template_view', name="campaign_monitor.template_view"),
    url(r'^campaigns/$', 'views.campaign_index', name="campaign_monitor.campaign_index"),
    url(r'^campaigns/sync/$', 'views.campaign_sync', name="campaign_monitor.campaign_sync"),
    url(r'^campaigns/(?P<campaign_id>[\w\-\/]+)/$', 'views.campaign_view', name="campaign_monitor.campaign_view"),
)
