# python
from datetime import datetime

# django
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

# local
from photologue.models import *
from tagging.fields import TagField
from perms.models import AuditingBaseModel

class PhotoSet(AuditingBaseModel):
    """
    A set of photos
    """
    PUBLISH_CHOICES = (
        (1, _('Private')),
        (2, _('Public')),
    )
    name = models.CharField(_('name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    publish_type = models.IntegerField(_('publish_type'), choices=PUBLISH_CHOICES, default=2)
    tags = TagField() # blank = True
    author = models.ForeignKey(User)
    update_dt = models.DateTimeField(auto_now=True)
    create_dt = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('photo set')
        verbose_name_plural = _('photo sets')
        permissions = (("view_photoset","Can view photoset"),)
    
    def get_cover_photo(self, *args, **kwargs):
        """ get latest thumbnail url """
        default_cover = settings.STATIC_URL + "/images/default-photo.jpg"
        try: cover_photo = self.image_set.latest('id').get_thumbnail_url()
        except: cover_photo = default_cover
        return cover_photo

    def check_perm(self, user, permission, *args, **kwargs):
        """
            has_perms(self, user, permission, *args, **kwargs)
            returns boolean
        """
        if user == self.author or user.has_perm(permission):
            return True
        return False

    @models.permalink
    def get_absolute_url(self):
        return ("photoset_details", [self.pk])

    def __unicode__(self):
        return self.name

class Image(ImageModel, AuditingBaseModel):
    """
    A photo with its details
    """
    SAFETY_LEVEL = (
        (1, _('Safe')),
        (2, _('Not Safe')),
    )
    title = models.CharField(_('title'), max_length=200)
    title_slug = models.SlugField(_('slug'))
    caption = models.TextField(_('caption'), blank=True)
    date_added = models.DateTimeField(_('date added'), auto_now_add=True, editable=False)
    is_public = models.BooleanField(_('public'), default=True, help_text=_('Public photographs will be displayed in the default views.'))
    member = models.ForeignKey(User, related_name="added_photos", blank=True, null=True)
    safetylevel = models.IntegerField(_('safety level'), choices=SAFETY_LEVEL, default=3)
    photoset = models.ManyToManyField(PhotoSet, blank=True, verbose_name=_('photo set'))
    tags = TagField()

    class Meta:
        permissions = (("view_image","Can view image"),)

    def save(self, *args, **kwargs):
        super(Image, self).save(*args, **kwargs)       
        # clear the cache
#        caching.instance_cache_clear(self, self.pk)
#        caching.cache_clear(PHOTOS_KEYWORDS_CACHE, key=self.pk)

#        # re-add instance to the cache
#        caching.instance_cache_add(self, self.pk)
   
    def delete(self, *args, **kwargs):
        super(Image, self).delete(*args, **kwargs)   
        # delete the cache
#        caching.instance_cache_del(self, self.pk)
#        caching.cache_delete(PHOTOS_KEYWORDS_CACHE)

    @models.permalink
    def get_absolute_url(self):
        photo_set = self.photoset.all()[0]
        return ("photo", [self.pk, photo_set.pk])

    def meta_keywords(self):
        pass
#        from base.utils import generate_meta_keywords
#        keywords = caching.cache_get(PHOTOS_KEYWORDS_CACHE, key=self.pk)    
#        if not keywords:
#            value = self.title + ' ' + self.caption + ' ' + self.tags
#            keywords = generate_meta_keywords(value)
#            caching.cache_add(PHOTOS_KEYWORDS_CACHE, keywords, key=self.pk)     
#        return keywords  

    def check_perm(self, user, permission, *args, **kwargs):
        """
            has_perms(self, user, permission, *args, **kwargs)
            returns boolean
        """
        if user == self.member or user.has_perm(permission):
            return True
        return False

    def get_next(self, set=None):
        # decide which set to pull from
        if set: images = Image.objects.filter(photoset=set, id__gt=self.id)
        else: images = Image.objects.filter(id__gt=self.id)
        images = images.values_list("id", flat=True)
        images = images.order_by('date_added')
        try: return Image.objects.get(id=min(images))
        except ValueError: return None

    def get_prev(self, set=None):
        # decide which set to pull from
        if set: images = Image.objects.filter(photoset=set, id__lt=self.id)
        else: images = Image.objects.filter(id__lt=self.id)
        images = images.values_list("id", flat=True)
        images = images.order_by('date_added')
        try: return Image.objects.get(id=max(images))
        except ValueError: return None

    def __unicode__(self):
        return self.title

class Pool(models.Model):
    """
    model for a photo to be applied to an object
    """

    photo = models.ForeignKey(Image)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    created_at = models.DateTimeField(_('created_at'), default=datetime.now)

    class Meta:
        # Enforce unique associations per object
        permissions = (("view_photopool","Can view photopool"),)
        unique_together = (('photo', 'content_type', 'object_id'),)
        verbose_name = _('pool')
        verbose_name_plural = _('pools')
