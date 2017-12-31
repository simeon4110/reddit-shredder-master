"""
Definition of views.
"""

from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest
from django.shortcuts import render, redirect

from app.forms import *
from app.models import RedditAccounts
from app.reddit_connection.reddit_connection import *


def home(request):
    """
    Renders the home page.

    :param request: The HTTP request object.
    :return: The rendered page.
    """
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'index.html',
        {
            'title': 'Home Page',
            'year': datetime.datetime.now().year,
            'auth': get_auth_url(),
        }
    )


@exception(logger)
def shredder(request):
    """
    Renders the shredder page. If the user is logged in, user is redirected to
    profile page, if not a page requiring the user to authorize their account
    is displayed.

    :param request: The HTTP request.
    :return: Depends on user's auth state.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Redirect authorized user's to their profile.
    if user.is_authenticated:
        messages.warning(request, "Registered users must use the manual shredder"
                                  " under 'Your Authorized Reddit Accounts'"
                                  " below.")

        return redirect(profile)

    # If a saved refresh token exists, redirect user to the shredder actual.
    if 'token' in request.session:
        return render(
            request,
            'shredder_working.html',
            {
                'title': 'The Shredder',
                'year': datetime.datetime.now().year,
                'form': RedditShredderForm(),
            }
        )

    # if user is neither registered nor authorized, return the
    # authorization page.
    return render(
        request,
        'shredder.html',
        {
            'title': 'Authorize Your Account',
            'year': datetime.datetime.now().year,
            'auth': get_auth_url(),
        }
    )


def signup(request):
    """
    Renders the signup page, handles and parses registration input and
    saves valid users to database.

    :param request: The HTTP request object.
    :return: The rendered page.
    """
    assert isinstance(request, HttpRequest)

    # capture the form if method is POST
    if request.method == 'POST':
        form = UserCreateForm(request.POST)

        # Use builtin form validator to check form data and save
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            email = form.cleaned_data.get('email')
            user = authenticate(username=username, password=raw_password)
            login(request, user)

            # redirects user to the reddit authorization page.
            return redirect(profile)

        # If form is not valid, return the Register page and render the
        # error messages.
        else:
            form = UserCreateForm(request.POST)
            return render(
                request,
                'signup.html',
                {
                    'title': 'Register',
                    'message': form.error_messages,
                    'form': form,
                    'year': datetime.datetime.now().year,
                }
            )
    # If method is not POST, render the Registration form.
    else:
        form = UserCreateForm()
        return render(
            request,
            'signup.html',
            {
                'title': 'Register',
                'form': form,
                'year': datetime.datetime.now().year,
            }
        )


def changelog(request):
    """
    Renders the changelog page.

    :param request: The HTTP request object.
    :return: The rendered page.
    """
    assert isinstance(request, HttpRequest)

    return render(
        request,
        'changelog.html',
        {
            'title': 'Changelog',
            'year': datetime.datetime.now().year
        }
    )


@exception(logger)
def shredder_function(request):
    """
    The actual shredder function.

    :param request: The HTTP request object.
    :return: The rendered page.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # initialize the form data
    form = RedditShredderForm(request.POST)

    # get the time value from the form
    if form.is_valid():
        time = form.cleaned_data.get('keep')

    # if the user is authenticated, retrieve token from user.Profile
    if user.is_authenticated is True:
        messages.warning(request, "Authorized users must use the account "
                                  "specific shredder. Please select an account "
                                  "below.")
        return redirect('profile')

    # Recover token from session store.
    token = request.session['token']

    # initialize an authenticated reddit connection
    reddit_conn = RedditConnection(state=None,
                                   code=None,
                                   token=token,
                                   time=time,
                                   )

    # Catch Reddit API errors.
    try:
        # get and display the user's username
        user_name = reddit_conn.get_data(user=True)

    except Exception as e:
        # Catch 400 HTTP response codes, delete token, and redirect to account
        # auth page.
        if e.response.status_code == 400:
            messages.warning(request, "Your account is no longer authorized."
                                      " please authorize your account to"
                                      " continue.")
            request.session['token'] = None
            return redirect('shredder')

        # Catch forbidden errors and redirect to the shredder.
        if e.response.status_code == 403:
            messages.warning(request, "Something went wrong, please report this"
                                      " error to josh@joshharkema.com")
            request.session['token'] = None
            return request('shredder')

        # Catch errors on Reddit's end, and redirect.
        if e.response.status_code == 503 or e.response.status_code == 502 or \
                e.response.status_code == 504:
            messages.warning(request, "Reddit is too busy to process this"
                                      " request, please try again later.")
            request.session['token'] = None
            return request('shredder')

    # run the shredder and retrieve the output
    output, skipped_count, deleted_count = reddit_conn.shredder()

    # Unset the session token.
    request.session['token'] = None

    # render the shredder_console page and results
    return render(
        request,
        'shredder_console.html',
        {
            'title': 'Shredder Output',
            'year': datetime.datetime.now().year,
            'user_name': user_name,
            'output': output,
            'skipped_count': skipped_count,
            'deleted_count': deleted_count,
        }
    )


@exception(logger)
@login_required
def profile(request):
    """
    Renders the user's profile.

    :param request: The HTTP request.
    :return: The user's profile.
    """
    assert isinstance(request, HttpRequest)

    # initialize the authenticated user.
    user = request.user
    # Get all of the user's authorized reddit accounts.
    accounts = RedditAccounts.objects.filter(user_id=user.id)

    # Ensure user is authenticated.
    if user.is_authenticated is True:
        return render(
            request,
            'profile.html',
            {
                'title': 'Settings',
                'year': datetime.datetime.now().year,
                'user': user,
                'accounts': accounts,
                'form': SchedulerForm,
                'p_form': RecordKeepingForm(),
                'k_form': KarmaExcludeForm(),
                'auth': get_auth_url(),
                'keep': RedditShredderForm,
            }
        )

    # if user is not authenticated, redirect to the login page.
    else:
        return redirect(login)


@exception(logger)
@login_required
def logs(request):
    """
    Renders the user's logs.

    :param request: The HTTP request.
    :return: The rendered logs page.
    """
    assert isinstance(request, HttpRequest)

    # initialize the authenticated user.
    user = request.user

    # Get user's log output.
    output = SchedulerOutput.objects.filter(user_id=user.id)

    # Ensure user is authenticated. Render logs.
    if user.is_authenticated is True:
        return render(
            request,
            'logs.html',
            {
                'title': 'Records',
                'year': datetime.datetime.now().year,
                'user': user,
                'output': output,
            }
        )


@exception(logger)
@login_required
def privacy(request):
    """
    Updates the user's privacy settings.

    :param request: The Http Request.
    :return: Redirect to profile.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # If the page is not rendered with POST, redirect to profile.
    if request.method != "POST":
        messages.warning(request, "Whoops, not sure how you got here.")
        return redirect('/profile/')

    # If the user is not logged in, redirect to the login page.
    if request.user.is_authenticated is False:
        messages.warning(request, "You must log in.")
        return redirect('/login/')

    # Get form data and user.id.
    form = RecordKeepingForm(request.POST)

    # If the form is valid, update user's record keeping preference.
    if form.is_valid():
        user.profile.user_id = user.id
        user.profile.record_keeping = form.cleaned_data.get('record_keeping')
        user.save()

        messages.success(request,
                         "Great Success! Your privacy preference is saved.")

        return redirect('/profile/')


@exception(logger)
@login_required
def karma_exclude(request):
    """
    Updates the user's karma_exclude setting (i.e. the karma level where posts
    are not deleted.)

    :param request: The HTTP Request.
    :return: A redirect to the profile + success message.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # If request method is not post, redirect to profile.
    if request.method != "POST":
        messages.warning(request, "Whoops, not sure how you got here.")
        return redirect('/profile/')

    # If the user is not logged in, redirect to the login page.
    if request.user.is_authenticated is False:
        messages.warning(request, "You must log in.")
        return redirect('/login/')

    # Get the form data and user.
    form = KarmaExcludeForm(request.POST)

    # If the form is valid, update the user's karma_exclude preference.
    if form.is_valid():
        user.profile.karma_exclude = form.cleaned_data.get('karma_exclude')
        user.save()

        messages.success(request,
                         "Great Success! Your karma threshhold has been saved.")

        return redirect('/profile/')


@exception(logger)
@login_required
def manual_exclude(request):
    """
    Allows users to manually exclude comments and submissions.

    :param request: The http request.
    :return: A page of the user's comments and subs, sorted by user_name.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Get the session key to query to DB cache.
    key = request.session.session_key

    # If the user is not logged in, redirect to the login page.
    if user.is_authenticated is False:
        messages.warning(request, "You must log in to access this page.")
        return redirect('/login/')

    # Catch and unset user unset requests. This is done via a simple GET
    # method, nothing fancy.
    if request.GET.get('unset') is not None:
        item_id = request.GET.get('unset')
        excluded = ExcludedItems.objects.filter(excluded_item_id=item_id)
        messages.success(request,
                         "Great success! The item has been removed from your "
                         "list of exclusions.")
        excluded.delete()
        return redirect('/profile/exclude/')

    # Catch and set the set requests.
    if request.GET.get('set') is not None:
        item_id = request.GET.get('set')
        excluded = ExcludedItems(user_id=user.id,
                                 excluded_item_id=item_id)
        messages.success(request,
                         "Great success! The item has been added to your list of"
                         "exclusions.")
        excluded.save()
        return redirect('/profile/exclude/')

    # Get a DB object of all the user's available Reddit accounts.
    accounts = RedditAccounts.objects.filter(user_id=user.id)

    # If the cache exists, populate the item_list with it.
    if cache.get(key + "_items") is not None:
        item_list = cache.get(key + "_items")

    # Otherwise, populate the list via the Reddit API.
    else:
        # Put all the comments and subs into the same list.
        item_list = []
        for account in accounts:
            for comment in get_comments(account.reddit_token):
                item_list.append(
                    (comment.id, comment.body, comment.score,
                     account.reddit_user_name))
            for submission in get_submissions(account.reddit_token):
                item_list.append(
                    (submission.id, submission.title, submission.score,
                     account.reddit_user_name))
        cache.set(key + '_items', item_list, 600)

    return render(
        request,
        'exclude.html',
        {
            'title': 'Saved Items',
            'accounts': accounts,
            'year': datetime.datetime.now().year,
            'output': item_list,
            'exclude': ExclusionSelector,
            'excluded': list(ExcludedItems.objects.filter(
                user_id=user.id).values_list('excluded_item_id', flat=True)),

        }
    )


@exception(logger)
@login_required
def delete(request):
    """
    Allows users to manually delete comments / subs.

    :param request: The http request.
    :return: A page of the user's comments and subs, sorted by user_name.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # If the user is not logged in, redirect to the login page.
    if user.is_authenticated is False:
        messages.warning(request, "You must log in to access this page.")
        return redirect('/login/')

    # Get the session key to query to DB cache.
    key = request.session.session_key

    if request.GET.get('delete') is not None:
        comment = request.GET.get('delete')
        user_name = request.GET.get('user_name')
        token = RedditAccounts.objects.filter(
            reddit_user_name=user_name).values_list('reddit_token', flat=True)
        message = delete_comment(comment, token)
        messages.success(request, message)

        # Clear the cache.
        if cache.get(key + "_comments") is not None:
            cache.delete(key + "_comments")

        return redirect('/profile/delete/')

    # Get a DB object of all the user's available Reddit accounts.
    accounts = RedditAccounts.objects.filter(user_id=user.id)

    # If the cache exists, populate the item_list with it.
    if cache.get(key + "_comments") is not None:
        item_list = cache.get(key + "_comments")

    # Otherwise, populate the list via the Reddit API.
    else:
        # Put all the comments and subs into the same list.
        item_list = []
        for account in accounts:
            for comment in get_comments(account.reddit_token):
                item_list.append(
                    (comment.id, comment.body, comment.score,
                     account.reddit_user_name))
        cache.set(key + '_comments', item_list, 600)

    return render(
        request,
        'delete.html',
        {
            'title': 'Manual Comment Deletion',
            'output': item_list,
            'year': datetime.datetime.now().year,
        }
    )


@exception(logger)
def authorize_callback(request):
    """
    Handles the callback from the Reddit API. Variably parses and saves the
    token to the user's profile or the request.session db.

    :param request: The HTTP request object.
    :return: The rendered HTTP page, depending on conditions passed in the
             request.
    """
    assert isinstance(request, HttpRequest)

    # If this is not a get request, raise an exception and shut down conn.
    if request.method != "GET":
        raise Exception

    # Ensure user is authenticated.
    if request.user.is_authenticated:
        user = request.user

        # Get the refresh_token by immediatly using the code to obtain auth.
        token = get_token(request.GET.get('code'))
        user_name = get_reddit_username(token)

        # Create a query set of all the reddit account objects.
        reddit_accounts = RedditAccounts.objects
        today = datetime.datetime.now(
            timezone.utc
        )

        # Iterate through all the reddit accounts, deleting any that match
        # the user's id and the auth'd reddit username.
        for item in reddit_accounts.all():
            if item.reddit_user_name == user_name:
                item.delete()

        # Create and save the data to a RedditAccount object in the SQL DB.
        user_accounts = RedditAccounts.objects.create()
        user_accounts.user_id = user.id
        user_accounts.reddit_user_name = user_name
        user_accounts.reddit_token = token
        user_accounts.authorized_date = today
        # Default schedule is None.
        user_accounts.schedule = "None"
        user_accounts.save()

        messages.success(request,
                         "Great Success! Your Reddit account was authorized"
                         " successfully.")

        # Redirect the user back to their profile.
        return redirect('profile')

    else:
        request.session['token'] = get_token(request.GET.get('code'))

        return redirect('shredder')
