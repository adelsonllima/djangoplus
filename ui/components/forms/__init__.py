# -*- coding: utf-8 -*-
import copy
from django.template import loader
from djangoplus.ui.components.forms.fields import *
from djangoplus.ui.components.forms import widgets
from django import forms as django_forms
from django.forms.forms import BoundField
from djangoplus.templatetags import mobile
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from djangoplus.utils.metadata import get_metadata, iterable, is_one_to_many, is_one_to_one

ValidationError = django_forms.ValidationError
DEFAULT_FORM_TITLE = u'Formulário'
DEFAULT_SUBMIT_LABEL = u'Enviar'


class Form(django_forms.Form):

    fieldsets = None

    def __init__(self, request, *args, **kwargs):
        metaclass = hasattr(self.__class__, 'Meta') and self.__class__.Meta or None
        self.request = request
        self.method = metaclass and hasattr(metaclass, 'method') and metaclass.method or 'post'
        self.horizontal = True
        self.id = self.__class__.__name__.lower()
        self.inline = kwargs.pop('inline', False)
        self.partial = kwargs.pop('partial', False)
        self.perm_or_group = ()
        self.str_hidden = ''
        self.inner_forms = []
        self.configured_fieldsets = []
        self.submit_label = DEFAULT_SUBMIT_LABEL
        self.title = DEFAULT_FORM_TITLE

        if self.method.lower() == 'post':
            kwargs['data'] = request.POST or None
            kwargs['files'] = request.FILES or None
        else:
            kwargs['data'] = request.GET or None

        if request.GET.get('popup'):
            prefix = kwargs.get('prefix', '')
            prefix = 'popup%s' % prefix
            kwargs.update(prefix=prefix)

        super(Form, self).__init__(*args, **kwargs)

        if hasattr(self, 'instance') and not self.fieldsets and not self.inline:
            self.fieldsets = copy.deepcopy(get_metadata(self._meta.model, 'fieldsets', ()))

        if metaclass:
            self.title = hasattr(metaclass, 'title') and metaclass.title or ''
            self.icon = hasattr(metaclass, 'icon') and metaclass.icon or ''
            self.note = hasattr(metaclass, 'note') and metaclass.note or ''
            self.horizontal = hasattr(metaclass, 'horizontal') and metaclass.horizontal or False
            self.perm_or_group = hasattr(metaclass, 'perm_or_group') and iterable(metaclass.perm_or_group) or self.perm_or_group

            if hasattr(metaclass, 'submit_label'):
                self.submit_label = metaclass.submit_label
            elif hasattr(self, 'instance'):
                self.submit_label = self.instance.pk and u'Atualizar' or u'Cadastrar'

            self.submit_style = hasattr(metaclass, 'submit_style') and metaclass.submit_style or 'default'
            self.method = hasattr(metaclass, 'method') and metaclass.method or 'post'

        for field_name in self.fields:
            if self.method.lower() == 'post' and field_name in self.request.GET:
                # field.widget = django_forms.HiddenInput()
                self.initial[field_name] = self.request.GET[field_name]

    def contextualize(self):

        for field_name in self.fields:
            field = self.fields[field_name]
            if hasattr(field, 'queryset'):
                if type(field) == django_forms.ModelMultipleChoiceField:
                    field.widget = MultipleModelChoiceField(field.queryset)
                if type(field) == CurrentUserField:
                    field.queryset = field.queryset.filter(pk=self.request.user.pk)
                    self.initial[field_name] = self.request.user.pk

                # if it is a model form
                if hasattr(self, 'instance'):
                    obj = None
                    role_username = get_metadata(field.queryset.model, 'role_username')
                    if role_username and self.request.user.groups.filter(name=field.queryset.model._meta.verbose_name):
                        obj = field.queryset.model.objects.get(**{role_username: self.request.user.username})
                    for subclass in field.queryset.model.__subclasses__():
                        role_username = get_metadata(subclass, 'role_username')
                        if role_username and self.request.user.groups.filter(name=subclass._meta.verbose_name):
                            obj = subclass.objects.get(**{role_username: self.request.user.username})
                    if obj:
                        groups = self.request.user.find_groups(self.perm_or_group, get_metadata(obj.__class__, 'verbose_name'))
                        # if the user is not superuser or there is only one group that allows the user to register the object
                        if not self.request.user.is_superuser and not groups.exists():
                            field.widget = widgets.HiddenInput(attrs={'value': obj.pk})
                            # field.widget = widgets.DisplayInput(obj)
                            continue

                if self.request.user.is_authenticated and (not hasattr(field, 'ignore_lookup') or not field.ignore_lookup):
                    if hasattr(self, 'instance'):
                        field.queryset = field.queryset.all(self.request.user, obj=self.instance)

                if True:#hasattr(field.queryset.model._meta, 'organization_lookup') or hasattr(field.queryset.model,'organization_ptr'):
                    from djangoplus.admin.models import Organization
                    if issubclass(field.queryset.model, Organization) and field.queryset.count() == 1:
                        if not isinstance(field, MultipleModelChoiceField):
                            obj = field.queryset[0]
                            field.widget = widgets.HiddenInput(attrs={'value': obj.pk})
                            # field.widget = widgets.DisplayInput(obj)

                if True:# hasattr(field.queryset.model._meta, 'unit_lookup') or hasattr(field.queryset.model, 'unit_ptr'):
                    from djangoplus.admin.models import Unit
                    if issubclass(field.queryset.model, Unit) and field.queryset.count() == 1:
                        if not isinstance(field, MultipleModelChoiceField):
                            obj = field.queryset[0]
                            field.widget = widgets.DisplayInput(obj)

                if hasattr(field.widget, 'lazy') and mobile(self.request):
                    field.widget.lazy = False

            if type(self.fields[field_name]) in [ModelChoiceField, MultipleModelChoiceField]:
                self.fields[field_name].widget.user = self.request.user

    def configure(self):

        from djangoplus.ui.components.forms import factory

        hidden_fields = []

        one_to_one_fields = dict()
        one_to_many_fields = dict()
        for name in self.fields:
            field = self.fields[name]
            if type(field) == OneToOneField:
                one_to_one_fields[name] = field
                del (self.fields[name])
            elif type(field) == OneToManyField:
                one_to_many_fields[name] = field
                del (self.fields[name])

        if not self.fieldsets:
            fields = self.fields.keys() + one_to_one_fields.keys() + one_to_many_fields.keys()
            if self.inline:
                self.fieldsets = ((u'', {'fields': (fields, )}),)
            else:
                self.fieldsets = ((u'', {'fields': fields}),)

        fieldset_field_names = []
        extra_fieldset_field_names = []
        for title, fieldset in self.fieldsets:
            field_names = fieldset.get('fields', ())
            relation_names = fieldset.get('relations', ())
            for name_or_tuple in tuple(field_names) + tuple(relation_names):
                for name in iterable(name_or_tuple):
                    fieldset_field_names.append(name)
        for field_name in self.fields.keys():
            if field_name not in fieldset_field_names:
                extra_fieldset_field_names.append(field_name)
        if extra_fieldset_field_names:
            self.fieldsets += (u'Outros', {'fields': extra_fieldset_field_names, }),

        for title, fieldset in self.fieldsets:
            title = '::' in title and title.split('::')[1] or title
            field_names = fieldset.get('fields', ())
            relation_names = fieldset.get('relations', ())

            configured_fieldset = dict(title=title, tuples=[], one_to_one=[], one_to_many=[])

            for name_or_tuple in tuple(field_names) + tuple(relation_names):
                fields = []
                for name in iterable(name_or_tuple):
                    if name in self.fields:
                        field = self.fields[name]
                        bf = BoundField(self, field, name)
                        if bf.is_hidden:
                            hidden_fields.append(bf)
                        else:
                            if bf.label:
                                label = conditional_escape(force_unicode(bf.label))
                                if self.label_suffix:
                                    if label[-1] not in ':?.!':
                                        label += self.label_suffix
                                label = label or ''
                            else:
                                label = ''

                            help_text = field.help_text or u''
                            label = force_unicode(label)[0:-1]
                            label = field.required and '%s<span class="text-danger">*</span>' % label or label

                            d = dict(name=name, request=self.request, label=label, widget=bf,
                                     help_text=help_text)
                            fields.append(d)

                    elif name in one_to_one_fields:
                        field = one_to_one_fields[name]
                        one_to_one_id = getattr(self.instance, '%s_id' % name)
                        form = factory.get_one_to_one_form(self.request, self.instance, name, one_to_one_id,
                                                           partial=True, prefix=name)
                        required = field.required or form.data.get(form.prefix, None)
                        save = form.data.get(form.prefix, None)
                        if not required:
                            for field_name in form.fields:
                                form.fields[field_name].required = False
                        configured_fieldset['one_to_one'].append((field, form, required, save))
                        self.inner_forms.append(form)
                    elif name in one_to_many_fields:
                        field = one_to_many_fields[name]
                        one_to_many_forms = []
                        if self.instance.pk:
                            qs = getattr(self.instance, name).all()
                        else:
                            qs = field.queryset.filter(pk=0)
                        count = qs.count()
                        limit = 4
                        for i in range(0, limit):
                            instance = i < count and qs[i] or None
                            form = factory.get_one_to_many_form(self.request, self.instance, name, partial=True,
                                                                inline=True, prefix='%s%s' % (name, i),
                                                                instance=instance)
                            form.id = '%s-%s' % (name, i)
                            form.hidden = i > count
                            required = form.data.get(form.prefix, None)
                            if not required:
                                for field_name in form.fields:
                                    form.fields[field_name].required = False
                            one_to_many_forms.append(form)
                            self.inner_forms.append(form)
                        configured_fieldset['one_to_many'].append((field, one_to_many_forms))

                if len(fields) > 2 or mobile(self.request):
                    self.horizontal = False

                configured_fieldset['tuples'].append(fields)

            self.configured_fieldsets.append(configured_fieldset)
        self.str_hidden = u''.join([unicode(x) for x in hidden_fields])

    def is_valid(self, *args, **kwargs):
        self.contextualize()
        self.configure()
        valid = super(Form, self).is_valid(*args, **kwargs)
        for form in self.inner_forms:
            valid = form.is_valid(*args, **kwargs) and valid or False
        return valid

    def has_errors(self):
        if self.errors:
            return True
        for form in self.inner_forms:
            if form.errors:
                return True
        return False

    def __unicode__(self):
        if self.inline:
            for field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = self.fields[field_name].label
                self.fields[field_name].widget.attrs['data-placeholder'] = self.fields[field_name].label
        return loader.render_to_string('form.html', {'self': self}, request=self.request)


class ModelForm(Form, django_forms.ModelForm):

    def save(self, *args, **kwargs):
        setattr(self.instance, 'request', self.request)
        for model_field in get_metadata(self.instance, 'fields'):
            # Se para o campo em questão foi definido um valor default. Ex: BooleanField(default=True)
            if unicode(model_field.default) != u'django.db.models.fields.NOT_PROVIDED':
                value = model_field.default
                if callable(value):
                    value = value()
                # Se não há nenhum valor no atributo da instância em questão, então será adotado
                # o valor default definido pelo desenvolvedor.
                if getattr(self.instance, model_field.name) is None:
                    setattr(self.instance, model_field.name, value)
        kwargs.update(commit=False)
        instance = super(ModelForm, self).save(*args, **kwargs)
        instance._post_save_form = self
        instance.save()
        return instance

    def save_121_and_12m(self):
        for fieldset in self.configured_fieldsets:
            for field, form, required, save in fieldset.get('one_to_one', ()):
                if save:
                    form.save()
                elif form.instance.pk:
                    form.instance.delete()

            for field, one_to_many_forms in fieldset.get('one_to_many', ()):
                for form in one_to_many_forms:
                    if form.data.get(form.prefix, None):
                        form.save()
                    else:
                        if form.instance.pk:
                            form.instance.delete()

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', ())
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)
        self.localized_fields = getattr(options, 'localized_fields', None)
        self.labels = getattr(options, 'labels', None)
        self.help_texts = getattr(options, 'help_texts', None)
        self.error_messages = getattr(options, 'error_messages', None)
