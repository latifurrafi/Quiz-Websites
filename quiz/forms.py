"""The only thing a newcomer has to fill in: their name."""

import re

from django import forms

NAME_RE = re.compile(r"^[\w\s.'\-]+$", re.UNICODE)


class StartForm(forms.Form):
    name = forms.CharField(
        max_length=80,
        strip=True,
        error_messages={
            "required": "Please enter your name to begin.",
            "max_length": "That name is a little too long — 80 characters max.",
        },
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. Latifur Rahman",
                "autocomplete": "name",
                "autocapitalize": "words",
                "spellcheck": "false",
                "maxlength": "80",
                "class": "field-input",
                "aria-label": "Your full name",
            }
        ),
    )

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if len(name) < 2:
            raise forms.ValidationError("Please enter at least two characters.")
        if not NAME_RE.match(name):
            raise forms.ValidationError("Letters, spaces, hyphens and apostrophes only, please.")
        return name
