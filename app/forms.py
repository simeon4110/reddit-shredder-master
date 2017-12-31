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
    Sets the user's preferences for the manual shredder.
    """
    keep = forms.IntegerField(label=_('Time delay in hours'),
                              widget=forms.TextInput({
                                  'class': 'form-control',
                                  'placeholder': 'Time Delay in Hours'}))


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