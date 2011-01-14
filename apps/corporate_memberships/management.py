from django.db.models.signals import post_syncdb
#from django.contrib.contenttypes.models import ContentType
from perms.utils import update_admin_group_perms

# assign permissions to the admin auth group
def assign_permissions(app, created_models, verbosity, **kwargs):
    update_admin_group_perms()

from corporate_memberships import models as corporate_membership
post_syncdb.connect(assign_permissions, sender=corporate_membership)


from django.conf import settings
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("corp_memb_added", _("Corporate Membership Added"), 
                                        _("A corporate membership  has been added."))
        #notification.create_notice_type("corp_memb_paid", _("Payment Received for Corporate Membership"), 
        #                                _("Payment for a corporate membership has been received."))

    post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"