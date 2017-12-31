"""
Custom db model definitions for Django.
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """
    Extends the user model to include email and the karma exclude setting.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    email = models.EmailField()

    record_keeping = models.BooleanField(default=False)

    karma_exclude = models.IntegerField(max_length=None,
                                        default=0)


class SchedulerOutput(models.Model):
    """
    Model stores the outputs from the reddit shredder.
    """
    user_id = models.IntegerField(max_length=None,
                                  default=1)
    reddit_user_name = models.CharField(max_length=150)

    sub_comment_id = models.CharField(max_length=20)

    sub_comment_body = models.CharField(max_length=1000)

    sub_comment_status = models.CharField(max_length=20)

    op_run_time = models.DateTimeField(auto_now=False,
                                       null=True,
                                       blank=True
                                       )


class RedditAccounts(models.Model):
    """
    Model stores all the info related to Reddit Accounts
    """
    NONE = 'None'
    DAILY = 'Daily'
    WEEKLY = 'Weekly'
    MONTHLY = 'Monthly'

    CHOICES = (
        (NONE, 'None'),
        (DAILY, 'Daily'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
    )

    user_id = models.IntegerField(max_length=None,
                                  default=0)

    reddit_user_name = models.CharField(max_length=150)

    reddit_token = models.CharField(max_length=150)

    authorized_date = models.DateField(auto_now=True)

    schedule = models.CharField(
        max_length=7,
        choices=CHOICES,
        default=NONE,
    )


class ExcludedItems(models.Model):
    """
    Model for the manual comment/sub exclusions.
    """
    user_id = models.IntegerField(max_length=None,
                                  default=0)

    excluded_item_id = models.CharField(max_length=20)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Updates custom user model upon user creation.

    :param sender: Request.
    :param instance: Request.
    :param created: Request.
    :param kwargs: Request.
    :return:
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
