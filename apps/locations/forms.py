from locations.models import Location
from perms.forms import AuditingBaseForm

class LocationForm(AuditingBaseForm):
    class Meta:
        model = Location
        fields = (
        'location_name',
        'description',
        'contact',
        'address',
        'address2',
        'city',
        'state',
        'zipcode',
        'country',
        'phone',
        'fax',
        'email',
        'website',
        'latitude',
        'longitude',
        'hq',
        'entityid',
        'entityownerid',
        'status',
        'status_detail',
        )
   
    def __init__(self, user=None, *args, **kwargs): 
        self.user = user
        super(LocationForm, self).__init__(user, *args, **kwargs)
        
        
        
        