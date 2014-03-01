from django import forms
from django.core.validators import EMPTY_VALUES
from django.core.exceptions import ValidationError
from django.utils.text import capfirst
from djangotoolbox.fields import ListField

from djangotoolbox.fields import ListFormField

# Add a formfield method to djangotoolbox's ListField
# This is deliberately not part of ListField, because you can't be sure to cover all value types, e.g.
# if you have a list of dates then there's no sensible way to display that on a form, but
# we add this method which covers most use cases of this field in this project.

def listfield_formfield_method(self, **kwargs):
    """ If this field has choices, then we can use a multiple choice field.
        NB: The chioces must be set on *this* field, e.g. this_field = ListField(CharField(), choices=x)
        as opposed to: this_field = ListField(CharField(choices=x))
    """
    #Largely lifted straight from Field.formfield() in django.models.__init__.py
    defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
    if self.has_default(): #No idea what this does
        if callable(self.default):
            True
            defaults['initial'] = self.default
            defaults['show_hidden_initial'] = True
        else:
            defaults['initial'] = self.get_default()
    #if self.choices:
    if self.choices:
        form_field_class = forms.MultipleChoiceField
        defaults['choices'] = self.choices
    else:
        form_field_class = ListFormField
    defaults.update(**kwargs)
    return form_field_class(**defaults)


# Ditto as for formfield really
def listfield_validate_method(self, value_list, model_instance):
    """ We want to override the default validate method from django.db.fields.Field, because it
        is only designed to deal with a single choice from the user.
    """
    if not self.editable:
        # Skip validation for non-editable fields
        return
    #Validate choices
    if self.choices:
        valid_values = []
        for choice in self.choices:
            if isinstance(choice[0], (list, tuple)):
                #this is an optgroup, so look inside it for the options
                for optgroup_choice in choice[0]:
                    valid_values.append(optgroup_choice[0])
            else:
                valid_values.append(choice[0])
        for value in value_list:
            if value not in value_list:
                #TODO: if there is more than 1 invalid value then this should show all of the invalid values
                raise ValidationError(self.error_messages['invalid_choice'] % value)
    #Validate null-ness
    if value_list is None and not self.null:
        raise ValidationError(self.error_messages['null'])

    if not self.blank and value in EMPTY_VALUES:
        raise ValidationError(self.error_messages['blank'])


#Apply the monkey patches
ListField.formfield = listfield_formfield_method
ListField.validate = listfield_validate_method   #Override default

