import commands
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings

from metrics.models import Metric


class Command(BaseCommand):
    """
    Gather usage statistics about the site

    Statistics gathered:

    1. HDD space used from the shell
    2. Total users from auth_users
    3. Total members from auth_users
    4. Total visits from event_logs by day
    """
    def handle(self, *app_names, **options):
        """
        Handle gathering the statistics
        """
        verbosity = 1
        if 'verbosity' in options:
            verbosity = int(options['verbosity'])

        # cache the user/member totals
        self.users = self.get_users()
        self.members = self.get_members()

        # create a metric from the totals
        metric = Metric()
        metric.users = len(self.users)
        metric.members = len(self.members)
        metric.visits = len(self.get_visits())
        metric.disk_usage = self.get_site_size()

        if verbosity >= 2:
            print 'metric.users', metric.users
            print 'metric.members', metric.members
            print 'metric.visits', metric.visits
            print 'metric.disk_usage', metric.disk_usage

        metric.save()

    def get_users(self):
        """
        Get all users from the auth_users table
        """
        return User.objects.all()

    def get_members(self):
        """
        Get all members from the auth_users table
        """
        from perms.utils import is_member
        users = self.users or self.get_users()

        return [user for user in users if is_member(user)]

    def get_visits(self):
        """
        Get all visits that are not bots from event_logs

        1. Filter the visits by this month only
        2. Filter the visits by non-bots
        """
        from event_logs.models import EventLog
        today = date.today()

        filters = {
            'robot__exact': None,
            'create_dt__gt': today
        }

        return EventLog.objects.filter(**filters)

    def get_site_size(self):
        """
        Get the HDD usage of the entire site
        """
        cmd = 'du -s %s' % settings.PROJECT_ROOT
        size_in_kb = 0
        status, output = commands.getstatusoutput(cmd)

        if status == 0:
            size_in_kb = int(output.split()[0].strip())

        return size_in_kb * 1024
