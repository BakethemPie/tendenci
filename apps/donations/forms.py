from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from donations.models import Donation
from donations.utils import get_allocation_choices, get_payment_method_choices, get_preset_amount_choices
from site_settings.utils import get_setting

class DonationForm(forms.ModelForm):
    # get the payment_method choices from settings
    donation_amount = forms.CharField(error_messages={'required': 'Please enter the donation amount.'})
    payment_method = forms.CharField(error_messages={'required': 'Please select a payment method.'},
                                     widget=forms.RadioSelect(choices=(('check-paid', 'Paid by Check'), 
                                                              ('cc', 'Make Online Payment'),)), initial='cc', )
    company = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'size':'30'}))
    address = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'size':'35'}))
    state = forms.CharField(max_length=50, required=False,  widget=forms.TextInput(attrs={'size':'5'}))
    zip_code = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'size':'10'}))
    referral_source = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'size':'40'}))
    email = forms.EmailField(help_text='A valid e-mail address, please.')
    email_receipt = forms.BooleanField(initial=True)
    comments = forms.CharField(max_length=1000, required=False,
                               widget=forms.Textarea(attrs={'rows':'3'}))
    allocation = forms.ChoiceField()
    
    class Meta:
        model = Donation
        fields = ('donation_amount',
                  'payment_method',
                  'first_name',
                  'last_name',
                  'company',
                  'address',
                  'address2',
                  'city',
                  'state',
                  'zip_code',
                  'country',
                  'phone',
                  'email',
                  'email_receipt',
                  'allocation',
                  'referral_source',
                  'comments',
                  )
        
    def __init__(self, user, *args, **kwargs):
        super(DonationForm, self).__init__(*args, **kwargs)
        # populate the user fields
        if user and user.id:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            try:
                profile = user.get_profile()
                if profile:
                    self.fields['company'].initial = profile.company
                    self.fields['address'].initial = profile.address
                    self.fields['address2'].initial = profile.address2
                    self.fields['city'].initial = profile.city
                    self.fields['state'].initial = profile.state
                    self.fields['zip_code'].initial = profile.zipcode
                    self.fields['country'].initial = profile.country
                    self.fields['phone'].initial = profile.phone
            except:
                pass
            
        self.fields['payment_method'].widget = forms.RadioSelect(choices=get_payment_method_choices(user))
        allocation_str = get_setting('module', 'donations', 'donationsallocations')
        if allocation_str:
            self.fields['allocation'].choices = get_allocation_choices(user, allocation_str)
        else:
            del self.fields['allocation']
        preset_amount_str = (get_setting('module', 'donations', 'donationspresetamounts')).strip('')
        if preset_amount_str:
            self.fields['donation_amount'] = forms.ChoiceField(choices=get_preset_amount_choices(preset_amount_str))
            
            
    def clean_donation_amount(self):
        #raise forms.ValidationError(_(u'This username is already taken. Please choose another.'))
        try:
            if float(self.cleaned_data['donation_amount']) <= 0:
                raise forms.ValidationError(_(u'Please enter a positive number'))
        except:
            raise forms.ValidationError(_(u'Please enter a numeric positive number'))                       
        return self.cleaned_data['donation_amount']
        