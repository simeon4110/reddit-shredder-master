"""
Definition of views.
"""

import datetime
from datetime import timezone

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import render, redirect

from app.forms import *
from app.logger.exception_decor import exception
from app.logger.exception_logger import logger
from app.models import RedditAccounts
from app.reddit_connection.reddit_connection import delete_comment
from app.reddit_connection.reddit_connection import get_auth_url
from app.reddit_connection.reddit_connection import get_reddit_username
from app.reddit_connection.reddit_connection import get_token


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
    Renders the shredder page. If user is logged in the option to select an
    account is shown, otherwise the token saved in the session is used and used
    to determine the account to be used.

    :param request: The HTTP request.
    :return: Depends on user's auth state.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Catch and redirect user's without tokens / accounts. Redirect to the
    # authorize page.
    if 'token' not in request.session and user.is_authenticated is False:
        return render(
            request,
            'shredder.html',
            {
                'title': 'Authorize Your Account',
                'year': datetime.datetime.now().year,
                'auth': get_auth_url(),
            }
        )

    # Display the account selector to authorized users by adding the user.id
    # to the RedditShredderForm class.
    if user.is_authenticated:
        # If the user has no authorized accounts, add warning and redirect.
        if not RedditAccounts.objects.filter(user_id=user.id):
            messages.warning(request, "You haven't authorized an account, please"
                                      " authorize an account under 'Authorized "
                                      "Accounts' below to continue.")
            return redirect('profile')

        return render(
            request,
            'shredder_working.html',
            {
                'title': 'The Shredder',
                'year': datetime.datetime.now().year,
                'form': RedditShredderForm(user_id=user.id),
            }
        )

    # Render the one-off shredder for un-registered users (they're identical, I
    # separated them for semantic rather than programmatic reasons.)
    # :TODO: Create two separate forms to allow for proper validation.
    if 'token' in request.session:
        return render(
            request,
            'shredder_working.html',
            {
                'title': 'The Shredder',
                'year': datetime.datetime.now().year,
                'form': RedditShredderForm(user_id=None),
            }
        )


@exception(logger)
def shredder_output(request):
    """
    Renders the shredder output page, the actual shredding is done via an AJAX
    POST request to the run_shredder function in reddit_connection.py.

    :param request: The HTTP request.
    :return: Varies depending on auth state and request.method.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Add an info popup so people don't think the shredder has 'hung.'
    messages.info(request, "This process can take a while if the account being "
                           "shredded has a lot of comments and posts. Please "
                           "be patient.")

    # Catch non-POST calls to this page.
    if request.method != "POST":
        messages.warning(request, 'Whoops! Something unexpected happened.')
        return redirect(shredder)

    # If the user is authorized, pass the account + other vars to template.
    # :TODO: Form validation.
    if user.is_authenticated:
        account = request.POST.get('account')
        karma_limit = request.POST.get('karma_limit')
        time = request.POST.get('keep')

        return render(
            request,
            'shredder_console.html',
            {
                'title': 'Shredder Output',
                'year': datetime.datetime.now().year,
                'account': account,
                'karma_limit': karma_limit,
                'time': time,
            }
        )

    # If the user is not authorized, pass the main vars to template.
    else:
        karma_limit = request.POST.get('karma_limit')
        time = request.POST.get('keep')

        return render(
            request,
            'shredder_console.html',
            {
                'title': 'Shredder Output',
                'year': datetime.datetime.now().year,
                'karma_limit': karma_limit,
                'time': time,
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
@login_required
def profile(request):
    """
    Renders the user's profile.

    :param request: The HTTP request.
    :return: The user's profile.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Get all of the user's authorized reddit accounts.
    accounts = RedditAccounts.objects.filter(user_id=user.id)

    # Set initial form values dynamically.
    record_form = RecordKeepingForm(
        initial={'record_keeping': user.profile.record_keeping})
    karma_form = KarmaExcludeForm(
        initial={'karma_exclude': user.profile.karma_exclude})

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
                'p_form': record_form,
                'k_form': karma_form,
                'auth': get_auth_url(),
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
    if user.is_authenticated:
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
    Updates the user's privacy settings. Accessed via a POST request.

    :param request: The Http Request.
    :return: Redirect to profile with success / error message attached.
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

    # Get form data.
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
    :return: A redirect to the profile with success / error message attached.
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

    else:
        messages.warning(request, "Whoops! Something went wrong. You probably "
                                  "entered too large of a number, the max value "
                                  "for your Karma Threshold is 999999999.")

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

    # If the user is not logged in, redirect to the login page.
    if user.is_authenticated is False:
        messages.warning(request, "You must log in to access this page.")
        return redirect('/login/')

    # Catch and unset user unset requests. This is done via a simple GET
    # method, nothing fancy. User's are redirected to a clean URL.
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
                         " exclusions.")
        excluded.save()
        return redirect('/profile/exclude/')

    # Get a list of all of the user's exclusions.
    excluded = ExcludedItems.objects.filter(user_id=user.id).values_list(
        'excluded_item_id', flat=True)

    # Strip the list and append it to a clean array. I no longer remember why I
    # did it this way (JH).
    excluded_array = []
    for i in excluded:
        excluded_array.append(str(i))

    return render(
        request,
        'exclude.html',
        {
            'title': 'Saved Items',
            'year': datetime.datetime.now().year,
            'exclude': ExclusionSelector,
            'excluded': excluded_array,

        }
    )


@exception(logger)
@login_required
def delete(request):
    """
    Allows users to manually delete a comment / sub.

    :param request: The http request.
    :return: A page of the user's comments and subs, sorted by user_name.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # If the user is not logged in, redirect to the login page.
    if user.is_authenticated is False:
        messages.warning(request, "You must log in to access this page.")
        return redirect('/login/')

    # Catch get requests for delete.
    if request.GET.get('delete') is not None:
        comment = request.GET.get('delete')
        user_name = request.GET.get('user_name')
        item_type = request.GET.get('item_type')

        # Get the token associated with the Reddit username.
        token = RedditAccounts.objects.filter(
            reddit_user_name=user_name).values_list('reddit_token', flat=True)

        # Delete the comment / sub.
        message = delete_comment(comment, token, item_type)

        # Display the message from the delete function.
        messages.success(request, message)

        return redirect('/profile/delete/')

    return render(
        request,
        'delete.html',
        {
            'title': 'Manual Comment Deletion',
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

    # If an error message is returned, attach an error message and redirect.
    if request.GET.get('error'):
        messages.warning(request, 'You must authorize the shredder by clicking '
                                  '"allow" to continue. Please try again.')
        # If the user is authenticated, redirect to profile.
        if request.user.is_authenticated:
            return redirect('profile')
        # Otherwise, redirect to tha shredder_auth page.
        else:
            return redirect('shredder')

    # Ensure user is authenticated.
    if request.user.is_authenticated:
        user = request.user

        # Get the refresh_token by immediately using the code.
        token = get_token(request.GET.get('code'))
        # Immediately use the code, this catches errors of mis-adventure.
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


@login_required
def delete_account(request):
    """
    Purges all of a users data from all database tables, also deletes account.

    :param request: The HTTP request.
    :return: Redirect to login page.
    """
    assert isinstance(request, HttpRequest)

    user = request.user

    # Delete exclusions.
    try:
        excluded_items = ExcludedItems.objects.get(user_id=user.id)
        for item in excluded_items:
            item.delete()

    # Do nothing if there aren't any excluded items.
    except ExcludedItems.DoesNotExist or UnboundLocalError:
        pass

    # Delete Reddit Accounts.
    try:
        accounts = RedditAccounts.objects.get(user_id=user.id)
        if accounts:
            for item in accounts:
                item.delete()

    # Do nothing if no accounts exist.
    except RedditAccounts.DoesNotExist or UnboundLocalError:
        pass

    # Delete Scheduler Output.
    try:
        scheduler_output = SchedulerOutput.objects.get(user_id=user.id)
        if scheduler_output:
            for item in scheduler_output:
                item.delete()

    # Do nothing if no output exists.
    except SchedulerOutput.DoesNotExist or UnboundLocalError:
        pass

    # Delete profile
    user.profile.delete()

    # Delete Auth profile.
    user.delete()

    messages.success(request, "Your account has been successfully deleted.")
    return redirect('login')
