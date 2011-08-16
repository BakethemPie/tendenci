import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.contrib.auth.tokens import default_token_generator
from django.template import Context, loader
from django.utils.http import int_to_base36

from captcha.fields import CaptchaField
from registration.forms import RegistrationForm
from profiles.models import Profile
from registration.models import RegistrationProfile
from site_settings.utils import get_setting
from accounts.utils import send_registration_activation_email


class RegistrationCustomForm(RegistrationForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    company = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size':'40'}), required=False)
    phone = forms.CharField(max_length=50, required=False)
    address = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'size':'40'}), required=False)
    city = forms.CharField(max_length=50, required=False)
    state = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'size':'10'}), required=False)
    country = forms.CharField(max_length=50, required=False)
    zipcode = forms.CharField(max_length=50, required=False)
    captcha = CaptchaField()

    def save(self, profile_callback=None):
        # 
        #new_user = RegistrationProfile.objects.create_inactive_user(username=self.cleaned_data['username'],
        #                                                            password=self.cleaned_data['password1'],
        # create inactive user                                                           email=self.cleaned_data['email'])
        new_user = User.objects.create_user(self.cleaned_data['username'],
                                            self.cleaned_data['email'],
                                            self.cleaned_data['password1'])
        
        new_user.first_name = self.cleaned_data['first_name']
        new_user.last_name = self.cleaned_data['last_name']
        new_user.is_active = False
        new_user.save()
        # create registration profile
        registration_profile = RegistrationProfile.objects.create_profile(new_user)
        send_registration_activation_email(new_user, registration_profile)
        
        new_profile = Profile(user=new_user, 
                              email=self.cleaned_data['email'],
                              company=self.cleaned_data['company'],
                              phone=self.cleaned_data['phone'],
                              address=self.cleaned_data['address'],
                              city=self.cleaned_data['city'],
                              state=self.cleaned_data['state'],
                              country=self.cleaned_data['country'],
                              zipcode=self.cleaned_data['zipcode'],
                              )
        user_hide_default = get_setting('module', 'users', 'usershidedefault')
        if user_hide_default:
            new_profile.hide_in_search = 1
            new_profile.hide_address = 1
            new_profile.hide_email = 1
            new_profile.hide_phone = 1 
          
        new_profile.creator = new_user
        new_profile.creator_username = new_user.username
        new_profile.owner = new_user
        new_profile.owner_username = new_user.username
        new_profile.save()
                    
        return new_user
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        password_regex = get_setting('module', 'users', 'password_requirements_regex')
        password_requirements = get_setting('module', 'users', 'password_text')
        if password_regex:
            if not re.match(password_regex, password1):
                raise forms.ValidationError(mark_safe("The password does not meet the requirements </li><li>%s" % password_requirements))

        return password1
    
class LoginForm(forms.Form):

    username = forms.CharField(label=_("Username"), max_length=30, widget=forms.TextInput())
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False))
    #remember = forms.BooleanField(label=_("Remember Me"), help_text=_("If checked you will stay logged in for 3 weeks"), required=False)
    remember = forms.BooleanField(label=_("Remember Login"), required=False)

    user = None
    
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        # check if we need to hide the remember me checkbox
        # and set the default value for remember me
        hide_remember_me = get_setting('module', 'users', 'usershiderememberme')
        remember_me_default_checked = get_setting('module', 'users', 'usersremembermedefaultchecked')
        
        if remember_me_default_checked:
            self.fields['remember'].initial = True
        if hide_remember_me:
            self.fields['remember'].widget = forms.HiddenInput()
           
    def clean(self):
        if self._errors:
            return
        user = authenticate(username=self.cleaned_data["username"], password=self.cleaned_data["password"])
        
        if user:
            try:
                profile = user.get_profile()
            except Profile.DoesNotExist:
                profile = Profile.objects.create_profile(user=user)
           
            if user.is_active and profile.status==1 and profile.status_detail.lower()=='active':
                self.user = user
            else:
                raise forms.ValidationError(_("This account is currently inactive."))
        else:
            raise forms.ValidationError(_("The username and/or password you specified are not correct."))
        return self.cleaned_data

    def login(self, request):
        if self.is_valid():
            login(request, self.user)
            request.user.message_set.create(message=ugettext(u"Successfully logged in as %(username)s.") % {'username': self.user.username})
            if self.cleaned_data['remember']:
                request.session.set_expiry(60 * 60 * 24 * 7 * 3)
            else:
                request.session.set_expiry(0)
                
            return True
        return False
    
class PasswordResetForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), max_length=75)

    def clean_email(self):
        """
        Validates that a user exists with the given e-mail address.
        """
        email = self.cleaned_data["email"]
        self_reg = get_setting('module', 'users', 'selfregistration')
        self.users_cache = User.objects.filter(email__iexact=email)
        if len(self.users_cache) == 0:
            if self_reg:
                raise forms.ValidationError(mark_safe(_('That e-mail address doesn\'t have an associated user account. Are you sure you\'ve <a href="/accounts/register" >registered</a>?')))
            else:
                raise forms.ValidationError(_("That e-mail address doesn't have an associated user account."))
        return email

    def save(self, email_template_name='registration/password_reset_email.html', **kwargs):
        """
        Generates a one-use only link for resetting password and sends to the user
        """
        from django.core.mail import send_mail
        
        domain_override = kwargs.get('domain_override', False)
        use_https = kwargs.get('use_https', False)
        token_generator = kwargs.get('token_generator', default_token_generator)
        
        
        for user in self.users_cache:
            if not domain_override:
                site_name = get_setting('site', 'global', 'sitedisplayname')
            else:
                site_name  = domain_override
            site_url = get_setting('site', 'global', 'siteurl')
            t = loader.get_template(email_template_name)
            c = {
                'email': user.email,
                'site_url': site_url,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
            }
            from_email = get_setting('site', 'global', 'siteemailnoreplyaddress')
            send_mail(_("Password reset on %s") % site_name,
                t.render(Context(c)), from_email, [user.email])