from registry import site
from registry.base import CoreRegistry, lazy_reverse
from models import File


class FileRegistry(CoreRegistry):
    version = '1.0'
    author = 'Schipul - The Web Marketing Company'
    author_email = 'programmers@schipul.com'
    description = 'Stores file links and infomation for files ' \
                  'uploaded through wysiwyg and other parts in ' \
                  'the system'
    icon = '/site_media/static/images/icons/files-color-64x64.png'

    url = {
        'add': lazy_reverse('file.add'),
        'search': lazy_reverse('file.search'),
    }

site.register(File, FileRegistry)
