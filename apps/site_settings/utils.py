# django
from django.core.cache import cache

# local
from site_settings.models import Setting
from site_settings.cache import SETTING_PRE_KEY

def delete_all_settings_cache():
    keys = [SETTING_PRE_KEY, 'all']
    key = '.'.join(keys) 
    cache.delete(key)
    
def cache_setting(scope, scope_category, name, value):
    """
        Caches a single setting within a scope
        and scope category
    """
    keys = [SETTING_PRE_KEY, scope, 
            scope_category, 
            name]
    key = '.'.join(keys)   
    is_set = cache.add(key, value)
    if not is_set:
        cache.set(key, value)
    
def cache_settings(scope, scope_category):
    """
        Caches all settings within a scope
        and scope category
    """
    filters = {
        'scope': scope,
        'scope_category': scope_category,
    }
    settings = Setting.objects.filter(**filters)
    
    if settings:
        for setting in settings:
            keys = [SETTING_PRE_KEY, setting.scope, 
                    setting.scope_category, 
                    setting.name]
            key = '.'.join(keys)
            is_set = cache.add(key, setting.value)
            if not is_set:
                cache.set(key, setting.value)

def delete_setting_cache(scope, scope_category, name):
    """
        Deletes a single setting within a
        scope and scope category
    """
    keys = [SETTING_PRE_KEY, scope, 
            scope_category, 
            name]
    key = '.'.join(keys) 
    cache.delete(key)
    
def delete_settings_cache(scope, scope_category):
    """
        Deletes all settings within a scope
        and scope category
    """
    filters = {
        'scope': scope,
        'scope_category': scope_category,
    }
    settings = Setting.objects.filter(**filters)
    for setting in settings:
        keys = [SETTING_PRE_KEY, setting.scope, 
                setting.scope_category, 
                setting.name]
        key = '_'.join(keys)
        cache.delete(key)
        
def get_setting(scope, scope_category, name):
    """
        Gets a single setting value from within a scope
        and scope category
    """
    keys = [SETTING_PRE_KEY, scope, 
            scope_category, 
            name]
    key = '.'.join(keys)
    value = cache.get(key)
    if not value:
        filters = {
            'scope': scope,
            'scope_category': scope_category,
            'name': name
        }
        try:
            setting = Setting.objects.get(**filters)
        except:
            setting = None
        if setting:
            cache_setting(setting.scope, 
                          setting.scope_category,
                          setting.name,
                          setting.value)
        value = cache.get(key)
        if not value: value = ''
    return value