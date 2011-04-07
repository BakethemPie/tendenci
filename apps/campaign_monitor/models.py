from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from user_groups.models import Group, GroupMembership
from forms_builder.forms.models import FormEntry

class ListMap(models.Model):
    group = models.ForeignKey(Group)
    # list id for campaign monitor
    list_id = models.CharField(max_length=100)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
    last_sync_dt = models.DateTimeField(null=True)
    
class GroupQueue(models.Model):
    group = models.ForeignKey(Group)
    
class SubscriberQueue(models.Model):
    group = models.ForeignKey(Group)
    user = models.ForeignKey(User, null=True)
    subscriber = models.ForeignKey(FormEntry, null=True)


# create post_save and pre_delete signals to sync with campaign monitor
# http://www.campaignmonitor.com/api/getting-started/
# http://tendenci.createsend.com/subscribers/
# https://github.com/campaignmonitor/createsend-python/blob/master/createsend/list.py
 
cm_api_key = getattr(settings, 'CAMPAIGNMONITOR_API_KEY', None) 
cm_client_id = getattr(settings, 'CAMPAIGNMONITOR_API_CLIENT_ID', None)
if cm_api_key and cm_client_id:
    from createsend import CreateSend, List, Client, Subscriber, BadRequest
    CreateSend.api_key = cm_api_key
    
    def sync_cm_list(sender, instance=None, created=False, **kwargs):
        """On Group Add:
                if group name does not exist on C. M,
                    add a list to C. M.
                add an entry to listmap
                
            On Group Edit:
                if group exists on C. M.,
                    if list.name <> group.name,
                        update list name
                else:
                    add a list on C. M.
                    add an entry to listmap
        """
        
        cl = Client(cm_client_id)
        lists = cl.lists()
        list_ids = [list.ListID for list in lists]
        list_names = [list.Name for list in lists]
        list_ids_d = dict(zip(list_names, list_ids))
        list_d = dict(zip(list_ids, lists))
        
        if created:
            if instance.name in list_names:
                list_id = list_ids_d[instance.name]
                
            else:
                list_id = get_or_create_cm_list(cm_client_id, instance)
            
            if list_id:
                # add an entry to the listmap
                listmap_insert(instance, list_id)
                
            
        else:   # update
            try:
                # find the entry in the listmap
                list_map = ListMap.objects.get(group=instance)
                list_id = list_map.list_id
            except ListMap.DoesNotExist:
                if instance.name in list_names:
                    list_id = list_ids_d[instance.name]
                else:
                    # hasn't be created on C. M. yet. create one
                    list_id = get_or_create_cm_list(cm_client_id, instance)
                        
                  
                if list_id:  
                    listmap_insert(instance, list_id)
                    
            
            # if the list title doesn't match with the group name, update the list title
            if list_id and list_id in list_ids:
                list = list_d[list_id]
                if instance.name != list.Name:
                    list = List(list_id)
                    list.update(instance.name, "", False, "")
                        

    def delete_cm_list(sender, instance=None, **kwargs):
        """Delete the list from campaign monitor
        """
        if instance:
            try:
                list_map = ListMap.objects.get(group=instance)
                list_id = list_map.list_id
                list = List(list_id)
                
                if list:
                    list.delete()
                list_map.delete()
                
            except ListMap.DoesNotExist:
                pass
            
    def sync_cm_subscriber(sender, instance=None, created=False, **kwargs):
        """Subscribe the subscriber to the campaign monitor list
        """
        (name, email) = get_name_email(instance)
            
        if email:
            try:
                list_map = ListMap.objects.get(group=instance.group)
                list_id = list_map.list_id
                list = List(list_id)
                
                if list:
                    subscriber_obj = Subscriber(list_id)
                    
                    # check if this user has already subscribed, if not, subscribe it
                    try:
                        subscriber = subscriber_obj.get(list_id, email)
                    except BadRequest as br:
                        email_address = subscriber_obj.add(list_id, email, name, [], True)
                
            except ListMap.DoesNotExist:
                pass
    
    def delete_cm_subscriber(sender, instance=None, **kwargs):
        """Delete the subscriber from the campaign monitor list
        """
        (name, email) = get_name_email(instance)
        
        if email:
            try:
                list_map = ListMap.objects.get(group=instance.group)
                list_id = list_map.list_id
                list = List(list_id)
                
                if list:
                    subscriber_obj = Subscriber(list_id, email)
                    subscriber_obj.unsubscribe()
                   
            except ListMap.DoesNotExist:
                pass
            
    def listmap_insert(group, list_id, **kwargs):
        """Add an entry to the listmap
        """
        list_map = ListMap(group=group,
                           list_id=list_id)
        list_map.save()
        
    def get_or_create_cm_list(client_id, group):
        """Get or create the list on compaign monitor
        """
        try:
            # add the list with the group name to campaign monitor
            cm_list = List()
            list_id = cm_list.create(client_id, group.name, "", False, "")
        except:
            # add group to the queue for later process
            # might log exception reason in the queue
            gq = GroupQueue(group=group)
            gq.save()
            list_id = None
            
        return list_id
            
    def get_name_email(instance):
        if isinstance(instance, GroupMembership):
            email = instance.member.email
            name = instance.member.get_full_name()
        else:
            email = ""
            name = ""
        return (name, email)
            
        
            
    post_save.connect(sync_cm_list, sender=Group)   
    pre_delete.connect(delete_cm_list, sender=Group)
    
    post_save.connect(sync_cm_subscriber, sender=GroupMembership)   
    pre_delete.connect(delete_cm_subscriber, sender=GroupMembership)
    
    
    