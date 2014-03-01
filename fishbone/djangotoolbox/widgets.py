from django.forms import widgets
from django import forms
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe
from django.utils.html import escape


class BlobWidget(widgets.FileInput):
    def render(self, name, value, attrs=None):
        try:
            blob_size = len(value)
        except:
            blob_size = 0

        blob_size = filesizeformat(blob_size)
        original = super(BlobWidget, self).render(name, value, attrs=None)
        return mark_safe('%s<p>Current size: %s</p>' % (original, blob_size))
    
    
class ListWidget(forms.TextInput):
    """ A widget for being able to display a djangotoolbox.fields.ListField. """
    def render(self, name, value, attrs=None):
        if isinstance(value, (list, tuple)):               # ie/ if value is a list type then you can iterate over it
            value = u', '.join([unicode(v) for v in value])# Refractor from list/tuple to comma delimited
        if value is None:
            value = u""
        return super(ListWidget, self).render(name, value.encode('utf-8'), attrs)

class ListTextareaWidget(forms.Textarea):
    """ A widget for being able to display a list of strings as lines in a text area. """

    def render(self, name, value, attrs=None):
        if isinstance(value, (list, tuple)):
            value = u"\n".join([unicode(v) for v in value])
        return super(ListTextareaWidget, self).render(name, value, attrs)

def _render_iterable(iter):
    if isinstance(iter, dict):
        str_list = []
        for key, value in iter.iteritems():
            str_list.append('<li>%s: %s</li>' % (escape(key), _render_iterable(value)))
        return '<ul>%s</ul>' % ''.join(str_list)
    elif isinstance(iter, set):
        str_list = []
        for value in iter:
            str_list.append('<li>%s</li>' % _render_iterable(value))
        return '<ul>%s</ul>' % ''.join(str_list)
    elif isinstance(iter, list):
        str_list = []
        for value in iter:
            str_list.append('<li>%s</li>' % _render_iterable(value))
        return '<ol>%s</ol>' % ''.join(str_list)
    else:
        return escape(unicode(iter))


class AbstractIterableWidget(widgets.Input):
    def render(self, name, value, attrs=None):
        return mark_safe(_render_iterable(value))
