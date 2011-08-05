from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    """
    This script is to sync the groups and group subscribers with the campaign monitor 
    
    To run the command: python manage.py sync_campaign_monitor --verbosity 2
    """
    
    def handle(self, *args, **options):
        from user_groups.models import Group
        from subscribers.models import GroupSubscription as GS
        from campaign_monitor.models import ListMap, Campaign, Template
        from createsend import CreateSend, Client, List, Subscriber, \
            BadRequest, Unauthorized
        
        verbosity = 1
        if 'verbosity' in options:
            verbosity = options['verbosity']
            
        def subscribe_to_list(subscriber_obj, list_id, name, email):
            try:
                subscriber = subscriber_obj.get(list_id, email)
            except BadRequest as br:
                try:
                    email_address = subscriber_obj.add(list_id, email, name, [], True)
                    if verbosity >=2:
                            print "%s (%s)" % (name, email)
                except:
                    print name, email, ' - NOT ADDED'
        
        
        api_key = getattr(settings, 'CAMPAIGNMONITOR_API_KEY', None) 
        client_id = getattr(settings, 'CAMPAIGNMONITOR_API_CLIENT_ID', None)
        CreateSend.api_key = api_key
        
        cl = Client(client_id)
        lists = cl.lists()
        list_ids = [list.ListID for list in lists]
        list_names = [list.Name for list in lists]
        list_ids_d = dict(zip(list_names, list_ids))
        
        groups = Group.objects.filter(status=1, status_detail='active')
        listmaps = ListMap.objects.all()
        syncd_groups = [listmap.group for listmap in listmaps]
        cm_list = List()
        
        print "Starting to sync groups with campaign monitor..."
        print
        
        for group in groups:
            if group not in syncd_groups:
                # get the list id or create a list if not exists
                # campaing monitor requires the list title 
                if group.name in list_names:
                    list_id = list_ids_d[group.name]
                else:
                    # add group to the campaign monitor
                    list_id = cm_list.create(client_id, group.name, "", False, "")
                    print "Added group '%s' to the C.M. list." % group.name
                    print
                    
                # insert to the listmap
                list_map = ListMap(group=group,
                           list_id=list_id)
                list_map.save()
            else:
                list_map = ListMap.objects.filter(group=group)[0]
                list_id = list_map.list_id
                
            # if a previous added list is deleted on campaign monitor, add it back
            # TODO: we might need a setting to decide whether we want to add it back or not.
            
            a_list = List(list_id)
            try:
                list_stats = a_list.stats()
                #num_unsubscribed = list_stats.TotalUnsubscribes
                #if num_unsubscribed > 0:
                #    # a list of all unsubscribed
                #    unsubscribed_obj = a_list.unsubscribed('2011-5-1')
                #    unsubscribed_emails = [res.EmailAddress for res in unsubscribed_obj.Results]
                #    unsubscribed_names = [res.Name for res in unsubscribed_obj.Results]
                #   unsubscribed_list = zip(unsubscribed_emails, unsubscribed_names)
            except Unauthorized as e:
                if 'Invalid ListID' in e:
                    # this list might be deleted on campaign monitor, add it back
                    list_id = cm_list.create(client_id, group.name, "", False, "")
                    # update the list_map
                    list_map.list_id = list_id
                    list_map.save()
                    
                
            # sync subscribers in this group
            print "Subscribing users to the C.M. list '%s'..." % group.name
            members = group.members.all()
            subscriber_obj = Subscriber(list_id)
            for i, member in enumerate(members, 1):
                email = member.email
                name = member.get_full_name()
                
                subscribe_to_list(subscriber_obj, list_id, name, email)
            
            # sync subscribers in this group's subscription
            gss = GS.objects.filter(group=group)
            for gs in gss:
                form_entry = gs.subscriber
                (name, email) = form_entry.get_name_email()
                
                subscribe_to_list(subscriber_obj, list_id, name, email)
                    
        print 'Done'
        
        print 'Starting to sync campaigns with campaign monitor...'
        
        print 'Syncing sent campaigns...'
        sent = cl.campaigns()
        for c in sent:
            try:
                campaign = Campaign.objects.get(campaign_id = c.CampaignID)
                print "Updating campaign (%s - %s)" % (c.CampaignID, c.Name)
            except Campaign.DoesNotExist:
                print "Creating campaign (%s - %s)" % (c.CampaignID, c.Name)
                campaign = Campaign(campaign_id = c.CampaignID)
            campaign.subject = c.Subject
            campaign.name = c.Name
            campaign.sent_date = c.SentDate
            campaign.status = 'S'
            campaign.save()
        
        print 'Syncing scheduled campaigns...'
        if hasattr(cl,'scheduled'): scheduled = cl.scheduled()
        else: scheduled = []
        for c in scheduled:
            try:
                campaign = Campaign.objects.get(campaign_id = c.CampaignID)
                print "Updating campaign (%s - %s)" % (c.CampaignID, c.Name)
            except Campaign.DoesNotExist:
                print "Creating campaign (%s - %s)" % (c.CampaignID, c.Name)
                campaign = Campaign(campaign_id = c.CampaignID)
            campaign.subject = c.Subject
            campaign.name = c.Name
            campaign.status = 'C'
            campaign.save()
        
        print 'Syncing draft campaigns...'
        if hasattr(cl,'drafts'): drafts = cl.drafts()
        else: drafts = []
        for c in drafts:
            try:
                campaign = Campaign.objects.get(campaign_id = c.CampaignID)
                print "Updating campaign (%s - %s)" % (c.CampaignID, c.Name)
            except Campaign.DoesNotExist:
                print "Creating campaign (%s - %s)" % (c.CampaignID, c.Name)
                campaign = Campaign(campaign_id = c.CampaignID)
            campaign.subject = c.Subject
            campaign.name = c.Name
            campaign.save()
            
        print "Done"

        print 'Syncing templates...'
        if hasattr(cl,'templates'): templates = cl.templates()
        else: templates = []
        for t in templates:
            try:
                template = Template.objects.get(template_id = t.TemplateID)
                print "Updating campaign (%s - %s)" % (c.CampaignID, c.Name)
            except Template.DoesNotExist:
                print "Creating template (%s - %s)" % (t.TemplateID, t.Name)
                template = Template(template_id = t.TemplateID)
            template.name = t.Name
            template.cm_preview_url = t.PreviewURL
            template.cm_screenshot_url = t.ScreenshotURL
            template.save()
        
        print "Done"
