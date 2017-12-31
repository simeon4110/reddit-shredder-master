"""
This module iterates through the DB and shreds Reddit accounts based on
a pre-selected schedule. All timezones MUST be in UTC. If the timezones
mismatch, the entire program logic will fail.

Also handles requests to /profile/schedule, updating the user's schedule.

Written by Josh Harkema in December of 2017.
"""

from datetime import datetime
from multiprocessing import Process

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import redirect

from app.forms import SchedulerForm
from app.models import SchedulerOutput, RedditAccounts, ExcludedItems
from app.reddit_connection.reddit_connection import *


@exception(logger)
def change_schedule(request):
    """
    Processes requests to change an reddit accounts schedule.

    :param request: The request sent to the URL.
    :return: The profile page, rendered with a success message.
    """
    assert isinstance(request, HttpRequest)
    # If the page is not rendered with POST, redirect to profile.
    if request.method != "POST":
        messages.warning(request, "Whoops, not sure how you got here.")
        return redirect('/profile/')

    # If the user is not logged in, redirect to the login page.
    if request.user.is_authenticated is False:
        messages.warning(request, "You must log in.")
        return redirect('/login/')

    # Get the form data from the request.
    form = SchedulerForm(request.POST)

    if form.is_valid():
        # Get the id of the schedule change, and the new schedule interval.
        object_id = form.cleaned_data.get('object_id')
        new_schedule = form.cleaned_data.get('schedule')

        # Get all objects that match that ID, replace their schedule with the
        # new schedule and save.
        schedule = RedditAccounts.objects.get(pk=object_id)
        schedule.schedule = new_schedule
        schedule.save()

        # Add the success message.
        messages.success(request, "Great Success! Schedule Updated!")

        # Render the profile, as usual.
        return redirect('/profile/')


@exception(logger)
def save_output(id, item_id, item_body, user_name, status):
    """
    Saves auto shredder output to DB.

    :param id: The user's PK.
    :param item_id: The sub or comment ID.
    :param item_body: The comment body or submission title.
    :param user_name: The Reddit user name.
    :param status: DELETED or SKIPPED.
    :return: Nothing, writes directly to db.
    """
    output = SchedulerOutput(user_id=id,
                             sub_comment_id=item_id,
                             sub_comment_body=item_body,
                             op_run_time=datetime.datetime.utcnow(),
                             reddit_user_name=user_name,
                             sub_comment_status=status,
                             )

    output.save()


@exception(logger)
def get_item_time(item):
    """
    Converts a Reddit item timestamp with a datetime object in the UTC timezone.

    :param item: The timestamp in need of conversion.
    :return: A converted datetime object.
    """
    item_time = datetime.datetime.utcfromtimestamp(item)
    item_time = item_time.replace(tzinfo=pytz.utc)
    return item_time


@exception(logger)
def schedule_shredder(account):
    """
    Function runs the scheduled shreds by iterating through the db and
    deleting comments/subs based on the schedule set by the user. Must be
    called via run_shredder function.

    :return: Nothing, writes directly to DB.
    """
    # Verify all available tokens are valid.
    check_tokens()

    # Set the time delay, if time is None time = None.
    if account[1] != "None":
        # Daily schedule.
        if account[1] == "Daily":
            time = 24
        # Weekly schedule.
        if account[1] == "Weekly":
            time = 168
        # Monthly schedule.
        if account[1] == "Monthly":
            time = 672

    # Get the users account object.
    user = User.objects.get(pk=account[0])

    # Get exclusion params (karma_exclude = the karma threshold, excluded_list=
    # the manual comment/sub exclusions.)
    karma_exclude = user.profile.karma_exclude
    excluded_list = ExcludedItems.objects.filter(
        user_id=account[0]).values_list('excluded_item_id', flat=True)

    # Iterate through all comments.
    for comment in get_comments(account[3]):
        item_time = get_item_time(comment.created)
        if item_time < delta_now(time) and comment.score < karma_exclude \
                and comment.id not in excluded_list:
            if user.profile.record_keeping == 1:
                save_output(user.id,
                            comment.id,
                            comment.body,
                            user_name=account[2],
                            status="DELETED",
                            )
            comment.edit(string_generator())
            comment.delete()

        else:
            if user.profile.record_keeping == 1:
                save_output(user.id,
                            comment.id,
                            comment.body,
                            user_name=account[2],
                            status="SKIPPED")

    # Iterate through all submissions.
    for submission in get_submissions(account[3]):
        item_time = get_item_time(submission.created)
        if item_time < delta_now(time) and submission.score < karma_exclude \
                and submission.id not in excluded_list:
            if user.profile.record_keeping == 1:
                save_output(user.id,
                            submission.id,
                            submission.title,
                            user_name=account[2],
                            status="DELETED",
                            )
            submission.delete()

        else:
            if user.profile.record_keeping == 1:
                save_output(user.id,
                            submission.id,
                            submission.title,
                            user_name=account[2],
                            status="SKIPPED")


@exception(logger)
def check_tokens():
    """
    Verifies all Reddit tokens are working, deletes those that aren't.

    :return: Nothing.
    """
    accounts = RedditAccounts.objects.values_list('reddit_token', flat=True)

    for account in accounts:
        try:
            name = get_reddit_username(account)

        # :TODO: not this.
        except:
            bad_token = RedditAccounts.objects.filter(reddit_token=account)
            bad_token.delete()


@exception(logger)
def run_shredder():
    """
    Wrapper to add threading to the auto shredder jobs.

    :return: Nothing.
    """
    procs = []

    # Init proc for each account in the DB.
    for account in RedditAccounts.objects.values_list('user_id',
                                                      'schedule',
                                                      'reddit_user_name',
                                                      'reddit_token',
                                                      'id'):
        proc = Process(target=schedule_shredder(account))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()


@exception(logger)
def purge_db():
    """
    Purges old records from the DB to save space and protect user privacy.
    Deletes all records older than one day.

    :return: Noting, writes directly to DB.
    """
    model = SchedulerOutput.objects.all()

    for item in model:
        if item.op_run_time < delta_now(24):
            item.delete()
