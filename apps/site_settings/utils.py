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
    value = u''
    keys = [SETTING_PRE_KEY, scope, 
            scope_category, 
            name]
    key = '.'.join(keys)
    
    setting = cache.get(key)
    if setting:
        value = setting.value.strip()

        # convert data types
        if setting.data_type == 'boolean':
            value = value[0].lower() == 't'
        if setting.data_type == 'int':
            if value.strip(): value = int(value.strip())
            else: value = 0 # default to 0
                            
    if not value:
        try:
            filters = {
                'scope': scope,
                'scope_category': scope_category,
                'name': name
            }            

            setting = Setting.objects.get(**filters)
            cache_setting(setting.scope, setting.scope_category,setting.name,setting)
        except:
            setting = None
            
        if setting:
            value = setting.value.strip()
            
            # convert data types
            if setting.data_type == 'boolean':
                value = value[0].lower() == 't'
            if setting.data_type == 'int':
                if value.strip(): value = int(value.strip())
                else: value = 0 # default to 0
                
    return value

def check_setting(scope, scope_category, name):
    return Setting.objects.filter(scope=scope, 
        scope_category=scope_category, name=name).exists()

def get_form_list(user):
    """
    Generate a list of 2-tuples of form id and form title
    This will be used as a special select
    """
    from forms_builder.forms.models import Form
    forms = Form.objects.search(user=user)
    print forms
    #To avoid hitting the database n time by calling .object
    #We will use the values in the index field.
    l = []
    for form in forms:
        l.append((form.primary_key, form.title))
    
    return l
    
def get_box_list(user):
    """
    Generate a list of 2-tuples of form id and form title
    This will be used as a special select
    """
    from boxes.models import Box
    boxes = Box.objects.search(user=user)
    print boxes
    #To avoid hitting the database n time by calling .object
    #We will use the values in the index field.
    l = []
    for box in boxes:
        l.append((box.primary_key, box.title))
    
    return l
