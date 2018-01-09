"""
This module contains the functions used to connect to and manipulate the Reddit
API. All of the functions are documented below.
"""

import datetime
import random
import string
import uuid
from datetime import timezone

import praw
import pytz
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.utils.timezone import timedelta

from Reddit_Shredder.settings import CLIENT_ID
from Reddit_Shredder.settings import CLIENT_SECRET
from Reddit_Shredder.settings import REDIRECT_URI
from Reddit_Shredder.settings import USER_AGENT
from app.logger.exception_decor import exception
from app.logger.exception_logger import logger
from app.models import RedditAccounts

# Initialize Reddit object for non-authenticated functions.
reddit = praw.Reddit(client_id=CLIENT_ID,
                     client_secret=CLIENT_SECRET,
                     redirect_uri=REDIRECT_URI,
                     user_agent=USER_AGENT
                     )


@exception(logger)
def delete_comment(_id, token, item_type):
    """
    Manual deletion of a specific comment or sub. Comments are overwritten,
    submissions are not.

    :param _id: The comment or submission ID to be deleted.
    :param token: The user's saved refresh token.
    :param item_type: Comment / Submission
    :return: A success / error message. Depending on the result.
    """
    reddit_refresh = praw.Reddit(client_id=CLIENT_ID,
                                 client_secret=CLIENT_SECRET,
                                 refresh_token=token,
                                 user_agent=USER_AGENT
                                 )

    # Catch and delete submission types.
    if item_type == "Submission":
        submission = reddit_refresh.submission(_id)
        submission.delete()
        message = "Great Success! Submission deleted!"

    # Catch and delete comment types.
    elif item_type == "Comment":
        comment = reddit_refresh.comment(_id)
        comment.edit(string_generator())
        comment.delete()
        message = "Great Success! Comment overwritten and deleted!"

    # Otherwise, return an error.
    # :TODO: Better error handling.
    else:
        message = "Not sure what happened."

    return message


@exception(logger)
@login_required
def get_json_reddit(request):
    """
    Queries Reddit API and returns an array of dicts via JsonResponse. This is
    used to allow for AJAX loading on the API requests.

    :param request: The HTTP request.
    :return: JsonResponse of the API query (includes all of the user's comments
             and submissions for every account they have authorized.)
    """

    assert isinstance(request, HttpRequest)

    user = request.user

    # Get all of the user's reddit accounts.
    accounts = RedditAccounts.objects.filter(user_id=user.id).values_list(
        'reddit_token', flat=True)

    # Init an empty object to hold the output data.
    data = []

    # Iterate through all accounts.
    for account in accounts:
        # Get user_name as a string, this makes it possible to append it to
        # a dict key.
        user_name = str(get_reddit_username(account))

        # Get all the comments and append them to the list.
        for comment in get_comments(account):
            temp_data = {
                'cid': comment.id,
                'body': comment.body,
                'karma': comment.score,
                'user_name': user_name,
                'item_type': "Comment",
            }
            data.append(temp_data)

        # Get all the submission and append them to the list.
        for submission in get_submissions(account):
            temp_data = {
                'cid': submission.id,
                'body': submission.title,
                'karma': submission.score,
                'user_name': user_name,
                'item_type': "Submission",
            }
            data.append(temp_data)

    return JsonResponse(data, safe=False)


def run_shredder(request):
    """
    This is the manual shredder function. It is called via an AJAX request to
    the run_shredder function.
    :TODO: There needs to be better validation. But, this function can be called
           via an API request in its current state.

    :param request: The HTTP request.
    :return: A JsonResponse of the shredder's output.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Get the token from the user's account if the user is authorized.
    if user.is_authenticated:
        account = request.POST.get('account')
        account_object = RedditAccounts.objects.get(reddit_user_name=account)
        token = account_object.reddit_token

    # Otherwise, get the token from the session store.
    elif request.session['token']:
        token = request.session['token']

    # If none of these options exist, raise an error.
    else:
        raise Exception

    # Get the other required values from the POST request.
    keep = int(request.POST.get('keep'))
    karma_limit = int(request.POST.get('karma_limit'))
    delete_everything = request.POST.get('delete_everything')

    # stores the output from the shredding process.
    output = []

    # Delete everything if the user selects delete_everything. Also, use
    # the delete everything function if the user sets no karma_limit or keep
    # values.
    if delete_everything == 'on' or keep == 0 and karma_limit == 1:
        for comment in get_comments(token):
            temp_data = {
                'cid': comment.id,
                'body': comment.body,
                'status': 'DELETED',
            }
            comment.edit(string_generator())
            comment.delete()
            output.append(temp_data)

        for submission in get_submissions(token):
            temp_data = {
                'cid': submission.id,
                'body': submission.title,
                'status': 'DELETED',
            }
            submission.delete()
            output.append(temp_data)

        return JsonResponse(output, safe=False)

    # overwrites and deletes a user's comments.
    for comment in get_comments(token):
        # Get the comment creation time.
        time = datetime.datetime.fromtimestamp(comment.created)
        time = time.replace(tzinfo=pytz.utc)

        # this overwrites the comment, saves it and deletes it
        if time < delta_now(keep) and comment.score <= karma_limit:
            temp_data = {
                'cid': comment.id,
                'body': comment.body,
                'status': 'DELETED',
            }
            comment.edit(string_generator())
            comment.delete()
            output.append(temp_data)

        # skip the comment
        else:
            temp_data = {
                'cid': comment.id,
                'body': comment.body,
                'status': 'SKIPPED',
            }
            output.append(temp_data)

    # deletes a user's subs.
    for submission in get_submissions(token):
        # Get the submission creation time.
        time = datetime.datetime.fromtimestamp(submission.created)
        time = time.replace(tzinfo=pytz.utc)

        # delete the submission
        if time < delta_now(keep) and submission.score <= karma_limit:
            temp_data = {
                'cid': submission.id,
                'body': submission.title,
                'status': 'DELETED',
            }
            submission.delete()
            output.append(temp_data)

        # skip the submission
        else:
            temp_data = {
                'cid': submission.id,
                'body': submission.title,
                'status': 'SKIPPED',
            }
            output.append(temp_data)

    return JsonResponse(output, safe=False)


@exception(logger)
def get_auth_url():
    """
    Gets a valid auth URL from the Reddit API.

    :return: A valid authorization URL for the Reddit API.
    """
    return reddit.auth.url(['identity,edit,history,read'], uuid.uuid4(),
                           'permanent')


@exception(logger)
def get_token(code):
    """
    Creates a refresh token from an OAuth code.

    :param code: The code returned from the Reddit API.
    :return: A refresh token.
    """

    token = reddit.auth.authorize(code)

    return str(token)


@exception(logger)
def get_reddit_username(token):
    """
    Returns the user's Reddit username.

    :param token: The user's saved refresh token.
    :return: The user's Reddit username.
    """

    reddit_refresh = praw.Reddit(client_id=CLIENT_ID,
                                 client_secret=CLIENT_SECRET,
                                 refresh_token=token,
                                 user_agent=USER_AGENT
                                 )

    return reddit_refresh.user.me()


@exception(logger)
def get_comments(token):
    """
    Returns a comments object from PRAW.

    :param token: The user's saved refresh token.
    :return: A comments object from PRAW.
    """
    reddit_refresh = praw.Reddit(client_id=CLIENT_ID,
                                 client_secret=CLIENT_SECRET,
                                 refresh_token=token,
                                 user_agent=USER_AGENT
                                 )
    return reddit_refresh.user.me().comments.new(limit=None)


@exception(logger)
def get_submissions(token):
    """
    Returns a submissions object from PRAW.

    :param token: The user's refresh token.
    :return: A submissions object from PRAW.
    """
    reddit_refresh = praw.Reddit(client_id=CLIENT_ID,
                                 client_secret=CLIENT_SECRET,
                                 refresh_token=token,
                                 user_agent=USER_AGENT
                                 )
    return reddit_refresh.user.me().submissions.new(limit=None)


@exception(logger)
def string_generator(size=36, chars=string.ascii_letters + string.digits):
    """
    Generates a random string of numbers and letters.

    :param size: The length of the string.
    :param chars: The characters to include (default is letters and numbers.)
    :return: A string of random letters and numbers.
    """
    return "".join(random.choice(chars) for _ in range(size))


@exception(logger)
def delta_now(time):
    """
    Returns delay as time.now - time.

    :param time: The number of hours between now and the delta.
    :return: Now minus the delta.
    """
    # Convert time to int.
    time = int(time)

    # Get the delta and change the timezone to UTC.
    delta = datetime.datetime.now(tz=timezone.utc) - timedelta(hours=time)
    delta = delta.replace(tzinfo=pytz.utc)

    return delta
