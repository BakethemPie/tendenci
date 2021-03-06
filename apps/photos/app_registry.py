from registry import site
from registry.base import CoreRegistry, lazy_reverse
from photos.models import PhotoSet, Image

class PhotoRegistry(CoreRegistry):
    version = '1.0'
    author = 'Schipul - The Web Marketing Company'
    author_email = 'programmers@schipul.com'
    description = 'Upload photos for the world to see!'
    icon = '/site_media/static/images/icons/photo-albums-color-64x64.png'
    
    event_logs = {
        'photo':{
            'base':('990000','1774F1'),
            'add':('990100','2E82E3'),
            'edit':('990200','4690D5'),
            'delete':('990300','5D9EC7'),
            'search':('990400','4682B9'),
            'view':('990500','2E79D1'),
        }
    }
    
    url = {
        'add': lazy_reverse('photos_batch_add'),
        'search': lazy_reverse('photos_search'),
    }

class PhotoSetRegistry(CoreRegistry):
    version = '1.0'
    author = 'Schipul - The Web Marketing Company'
    author_email = 'programmers@schipul.com'
    description = 'Upload photos for the world to see!'
    icon = '/site_media/static/images/icons/photo-albums-color-64x64.png'
    
    event_logs = {
        'photosets':{
            'base':('991000','1374FF'),
            'add':('991100','2582FF'),
            'edit':('991200','3890FF'),
            'delete':('991300','4A9EFF'),
            'search':('991400','5DACFF'),
            'view':('991500','6FB9FF'),
        }
    }
    
    url = {
        'add': lazy_reverse('photoset_add'),
        'search': lazy_reverse('photoset_latest'),
    }

#site.register(Image, PhotoRegistry)
site.register(PhotoSet, PhotoSetRegistry)
