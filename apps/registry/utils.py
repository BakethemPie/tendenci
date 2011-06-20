from django.core.urlresolvers import reverse
from django.utils.functional import lazy

from site_settings.utils import check_setting, get_setting

lazy_reverse = lazy(reverse, str)


class RegisteredApps(object):
    """
    RegistredApps iterarable that represents all registered apps

    All registered apps exist in the objects iterable and are also
    categorized by core/plugins.

    apps = site.get_registered_apps()

    core_apps = registered_apps.core
    plugin_apps = registered_apps.plugin
    """
    def __init__(self, apps):
        self.all_apps = []
        self.core = []
        self.plugins = []

        # append core and plugin apps to
        # individual lists
        for model, registry in apps.items():

            setting_tuple = (
                'module',
                registry.fields['model']._meta.app_label,
                'enabled',
            )

            # enabled / has settings
            if check_setting(*setting_tuple):
                registry.fields['enabled'] = get_setting(*setting_tuple)
                registry.fields['has_settings'] = True
            else:
                registry.fields['enabled'] = True
                registry.fields['has_settings'] = False

            registry.fields['url'].update({
                'settings': lazy_reverse('settings.index', args=[
                    'module',
                    registry.fields['model']._meta.app_label
                ])
            })

            if registry.fields['app_type'] == 'plugin':
                self.plugins.append(registry.fields)

            if registry.fields['app_type'] == 'core':
                self.core.append(registry.fields)

            # append all apps for main iterable
            self.all_apps.append(registry.fields)

        # sort the applications alphabetically by
        # object representation
        key = lambda x: unicode(x)
        self.all_apps = sorted(self.all_apps, key=key)
        self.core = sorted(self.core, key=key)
        self.plugins = sorted(self.plugins, key=key)

    def __iter__(self):
        return iter(self.all_apps)

    def __len__(self):
        return len(self.all_apps)
