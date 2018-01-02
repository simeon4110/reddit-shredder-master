"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _

from app.models import *


class BootstrapAuthenticationForm(AuthenticationForm):
    """
    Authentication form which uses boostrap CSS.
    """
    username = forms.CharField(label=_('username'),
                               max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder': 'Password'}))


class RedditShredderForm(forms.Form):
    """
    Receives the user's preferences for the manual shredder.
    """

    # The account the user wants to shred (reddit_user_name).
    account = forms.ModelChoiceField(queryset=RedditAccounts.objects.none(),
                                     label=_('Select an Account'),
                                     widget=forms.Select({
                                         'class': 'form-control',
                                     }))

    def __init__(self, user_id, *args, **kwargs):
        """
        Extends the ShredderForm class to allow user_name to be selected and
        displayed dynamically in the form.

        :param user_id: The user's id.
        :param args: *
        :param kwargs: **
        """
        super(RedditShredderForm, self).__init__(*args, **kwargs)
        self.fields['account'].queryset = RedditAccounts.objects.filter(
            user_id=user_id).values_list('reddit_user_name', flat=True)

    # The time cut-off to limit the shredder.
    keep = forms.IntegerField(label=_('Time delay in hours'),
                              initial=0,
                              widget=forms.NumberInput({
                                  'class': 'form-control',
                                  'placeholder': 'Time Delay in Hours'
                              }))

    # The user's karma threshold preference.
    karma_limit = forms.IntegerField(label=_('Karma Threshold'),
                                     initial=0,
                                     widget=forms.NumberInput({
                                         'class': 'form-control',
                                         'placeholder': 'Karma Threshold',
                                     }))


class KarmaExcludeForm(forms.ModelForm):
    """
    Allows user's to set a Karma threshold.
    """

    class Meta:
        model = Profile
        fields = ['karma_exclude']
        labels = ({'karma_exclude': _('Karma Amount to Exclude')})
        widgets = {
            'karma_exclude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Karma'
            })
        }


class SchedulerForm(forms.ModelForm):
    """
    Allows user's to set auto-shred schedules for their accounts.
    """
    # Blank IntegerField to receive the comment / submission ID.
    object_id = forms.IntegerField()

    class Meta:
        model = RedditAccounts
        fields = ['schedule']
        labels = ({'schedule': _('Set Schedule')})
        widgets = {
            'schedule': forms.Select(attrs={
                'class': 'form-control',
            }),
        }


class RecordKeepingForm(forms.Form):
    """
    Allows user's to set their record keeping preferences.
    """
    CHOICES = (
        (True, 'Yes'),
        (False, 'No')
    )

    record_keeping = forms.ChoiceField(
        label=_("Privacy Setting"),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        choices=CHOICES,
    )


class UserCreateForm(UserCreationForm):
    """
    Overrides the builtin user creation form, adding email support.
    """
    # declare the fields you will show
    username = forms.CharField(label=_("Your Username"),
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'Username'}))
    # first password field
    password1 = forms.CharField(label=_("Your Password"),
                                widget=forms.PasswordInput({
                                    'class': 'form-control',
                                    'placeholder': 'Password'}))
    # confirm password field
    password2 = forms.CharField(label=_("Repeat Your Password"),
                                widget=forms.PasswordInput({
                                    'class': 'form-control',
                                    'placeholder': 'Confirm your password'}))
    email = forms.EmailField(label=_("Email Address"),
                             required=True,
                             widget=forms.EmailInput({
                                 'class': 'form-control',
                                 'placeholder': 'Email'}))

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "email")

    def save(self, commit=True):
        """
        Extends the base user model to include the email field.
        :param commit: True / False.
        :return: The modified user model.
        """
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class ExclusionSelector(forms.Form):
    """
    Allows user's to select specific posts to exclude from the auto-shredder.
    """
    object_id = forms.IntegerField()
    exclude = forms.BooleanField(required=False)
