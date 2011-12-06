from django.core.management.base import BaseCommand, CommandError

from site_settings.models import Setting


class Command(BaseCommand):
    """
    Query the site settings for the value of one or more settings.
    
    Usages: 
           query_site_settings name1 name2 name3 
           query_site_settings scope/scope_category/name1
           query_site_settings scope/scope_category/name1 scope/scope_category/name2
           ...
    
    
    """
    help = 'Query the site settings for the value of one or more settings'


    def handle(self, *args, **options):
        params_list = args
        site_url_setting = Setting.objects.get(**{
                    'name': 'siteurl',
                    'scope': 'site',
                    'scope_category': 'global'
                })
        return_str = site_url_setting.value
        
        for param in params_list:
            return_str += ','
            try:
                scope, scope_category, name = param.split('/')
            except ValueError:
                name = param
                scope = ''
                scope_category = ''
            if scope and scope_category:   
                settings = Setting.objects.filter(**{
                        'name': name,
                        'scope': scope,
                        'scope_category': scope_category
                    })
            else:
                settings = Setting.objects.filter(name=name)
            if not settings:
                return_str += 'NOT EXIST'
            else:
                setting = settings[0]
                return_str += setting.value
                
        print return_str