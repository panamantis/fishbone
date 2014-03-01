import widgets
from django import forms


class AbstractIterableField(forms.CharField):
    widget = widgets.AbstractIterableWidget
