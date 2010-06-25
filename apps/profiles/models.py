import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from timezones.fields import TimeZoneField
from perms.models import TendenciBaseModel
from entities.models import Entity

from profiles.managers import ProfileManager
         

class Profile(TendenciBaseModel):
    # relations
    user = models.ForeignKey(User, unique=True, related_name="profile", verbose_name=_('user'))
    guid = models.CharField(max_length=40, default=uuid.uuid1)
    entity = models.ForeignKey(Entity, blank=True, null=True)
    pl_id = models.IntegerField(default=1)
    member_number = models.CharField(_('member number'), max_length=50, blank=True)
    historical_member_number = models.CharField(_('historical member number'), max_length=50)
    
    # profile meta data
    time_zone = TimeZoneField(_('timezone'))
    language = models.CharField(_('language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    salutation = models.CharField(_('salutation'), max_length=15, blank=True, choices=(
                                                                                      ('Mr.', 'Mr.'),
                                                                                      ('Mrs.', 'Mrs.'),
                                                                                      ('Ms.', 'Ms.'),
                                                                                      ('Miss', 'Miss'),
                                                                                      ('Dr.', 'Dr.'),
                                                                                      ('Prof.', 'Prof.'),
                                                                                      ('Hon.', 'Hon.'),
                                                                                      ))
    initials = models.CharField(_('initials'), max_length=50, blank=True)
    display_name = models.CharField(_('display name'), max_length=120, blank=True)
    mailing_name = models.CharField(_('mailing name'), max_length=120, blank=True)
    company = models.CharField(_('company') , max_length=100, blank=True)
    position_title = models.CharField(_('position title'), max_length=50, blank=True)
    position_assignment = models.CharField(_('position assignment'), max_length=50, blank=True)
    sex = models.CharField(_('sex'), max_length=50, blank=True, choices=(('male', u'Male'),('female', u'Female')))
    address_type = models.CharField(_('address type'), max_length=50, blank=True)
    address = models.CharField(_('address'), max_length=150, blank=True)
    address2 = models.CharField(_('address2'), max_length=100, blank=True)
    city = models.CharField(_('city'), max_length=50, blank=True)
    state = models.CharField(_('state'), max_length=50, blank=True)
    zipcode = models.CharField(_('zipcode'), max_length=50, blank=True)
    country = models.CharField(_('country'), max_length=50, blank=True)
    county = models.CharField(_('county'), max_length=50, blank=True)
    phone = models.CharField(_('phone'), max_length=50, blank=True)
    phone2 = models.CharField(_('phone2'), max_length=50, blank=True)
    fax = models.CharField(_('fax'), max_length=50, blank=True)
    work_phone = models.CharField(_('work phone'), max_length=50, blank=True)
    home_phone = models.CharField(_('home phone'), max_length=50, blank=True)
    mobile_phone = models.CharField(_('mobile phone'), max_length=50, blank=True)
    email = models.CharField(_('email'), max_length=200,  blank=True)
    email2 = models.CharField(_('email2'), max_length=200,  blank=True)
    url = models.CharField(_('url'), max_length=100, blank=True)
    url2 = models.CharField(_('url2'), max_length=100, blank=True)
    dob = models.DateTimeField(_('date of birth'), null=True, blank=True)
    ssn = models.CharField(_('social security number'), max_length=50, blank=True)
    spouse = models.CharField(_('spouse'), max_length=50, blank=True)
    department = models.CharField(_('department'), max_length=50, blank=True)
    education = models.CharField(_('education'), max_length=100, blank=True)
    student = models.IntegerField(_('student'), null=True, blank=True)
    remember_login = models.BooleanField(_('remember login'))
    exported = models.BooleanField(_('exported'))
    direct_mail = models.BooleanField(_('direct mail'), default=False)
    notes = models.TextField(_('notes'), blank=True) 
    admin_notes = models.TextField(_('admin notes'), blank=True) 
    referral_source = models.CharField(_('referral source'), max_length=50, blank=True)
    hide_in_search = models.BooleanField(default=0)
    hide_address = models.BooleanField(default=0)
    hide_email = models.BooleanField(default=0)
    hide_phone = models.BooleanField(default=0)   
    first_responder = models.BooleanField(_('first responder'), default=0)
    agreed_to_tos = models.BooleanField(_('agrees to tos'), default=0)
    original_username = models.CharField(max_length=50)
    
    objects = ProfileManager()
    
    def __unicode__(self):
        return self.user.username
    
    def get_absolute_url(self):
        return ('profile', [self.user.username])
    
    class Meta:
        permissions = (("view_profile","Can view profile"),)
        
    def is_admin(self):
        if hasattr(self.user, 'is_admin'):
            return getattr(self.user, 'is_admin')
        else:
            if self.user.is_superuser and self.user.is_active and self.status==1 \
                    and self.status_detail=='active':
                setattr(self.user, 'is_admin', True)
                return True
            else:
                setattr(self.user, 'is_admin', False)
                return False
        
    def is_developer(self):
        if self.user.is_superuser and self.user.is_staff and self.user.is_active \
            and self.status==1 and self.status_detail=='active':
            setattr(self.user, 'is_developer', True)
            return True
        else:
            setattr(self.user, 'is_developer', False)
            return False
        
    # if this profile allows view by user2_compare
    def allow_view_by(self, user2_compare):
        boo = False
       
        if user2_compare.is_superuser:
            boo = True
        else: 
            if user2_compare == self.user:
                boo = True
            else:
                if self.creator == user2_compare or self.owner == user2_compare:
                    if self.status == 1:
                        boo = True
                else:
                    if user2_compare.has_perm('profiles.view_profile', self):
                        boo = True
            
        return boo
    
    # if this profile allows edit by user2_compare
    def allow_edit_by(self, user2_compare):
        if user2_compare.is_superuser:
            return True
        else: 
            if user2_compare == self.user:
                return True
            else:
                if self.creator == user2_compare or self.owner == user2_compare:
                    if self.status == 1:
                        return True
                else:
                    if user2_compare.has_perm('profiles.change_profile', self):
                        return True
        return False
            
