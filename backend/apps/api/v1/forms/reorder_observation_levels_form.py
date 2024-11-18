from django import forms


class ReorderObservationLevelsForm(forms.Form):
    ordered_entities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40}),
        help_text="Enter entity names one per line in desired order",
    )