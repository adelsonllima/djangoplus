# -*- coding: utf-8 -*-
import copy
from djangoplus.ui.components import forms
from djangoplus.ui import Component
from djangoplus.utils import permissions
from django.db.models.aggregates import Sum
from djangoplus.utils.tabulardata import tolist
from djangoplus.utils.formatter import normalyze
from djangoplus.ui.components.dropdown import ModelDropDown, GroupDropDown
from djangoplus.utils.http import CsvResponse, XlsResponse, ReportResponse, mobile
from djangoplus.utils.metadata import get_metadata, get_field, get_fiendly_name, find_model, should_filter_or_display, \
    getattr2


class Paginator(Component):
    def __init__(self, request, qs, title=None, list_display=None, list_filter=None, search_fields=None,
                 list_per_page=25, list_subsets=None, exclude=None, to=None, readonly=False, is_list_view=False):

        super(Paginator, self).__init__(request)

        self.id = abs(hash(title))
        self.qs = qs.all()
        self.title = title
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.list_per_page = list_per_page
        self.list_subsets = list_subsets
        self.exclude = exclude
        self.to = to
        self.readonly = readonly
        self.is_list_view = is_list_view
        self.icon = get_metadata(qs.model, 'icon', None)
        self.list_total = get_metadata(qs.model, 'list_total', None)

        self.subset_actions = []
        self.filters = []
        self.pagination = ''

        self.original_qs = qs

        # list display
        self._configure_list_display()

        # column names
        self.column_names = []
        self._configure_column_names()

        # tabs
        self.tabs = []
        self.current_tab = self._get_from_request('tab', None)
        self._load_tabs()

        # drop down
        self.paginator_dropdown = GroupDropDown(request)
        self.subset_dropdown = GroupDropDown(request)
        self.drop_down = ModelDropDown(request, qs.model)
        self.mobile = mobile(self.request)

        if hasattr(self.qs, 'permission_map'):
            self.permission_map = self.qs.permission_map
        self.qs = self._filter_queryset(self.qs)

    def has_customized_template(self):
        return get_metadata(self.qs.model, 'list_template') is not None

    def get_current_tab_name(self):
        if len(self.tabs) > 1:
            if self.current_tab and self.current_tab != 'all':
                return self.current_tab
        return ''
    
    def get_tab(self):
        return self._get_from_request('tab', '')
    
    def get_search_fields(self):
        if self.search_fields is not None:
            return self.search_fields
        return get_metadata(self.qs.model, 'search_fields', [])
    
    def get_list_filter(self):
        if self.list_filter is None:
            self.list_filter = copy.deepcopy(get_metadata(self.qs.model, 'list_filter', None))
            if self.list_filter is None:
                self.list_filter = []
                for field in get_metadata(self.qs.model, 'fields'):
                    if hasattr(field, 'rel') and field.rel:
                        if not field.name.endswith('_ptr') and field.name != self.rel:
                            self.list_filter.append(field.name)
                    elif hasattr(field, 'choices') and field.choices:
                        self.list_filter.append(field.name)
                    elif type(field).__name__ in ['BooleanField', 'NullBooleanField', 'DateField', 'DateTimeField']:
                        self.list_filter.append(field.name)
        return self.list_filter

    def get_filter_form(self):
        form = forms.Form(self.request)
        form.title = 'Filtros'
        form.icon = 'fa-filter'
        form.partial = True
        self.filters = []
        for list_filter in self.get_list_filter():
            if type(list_filter) in (tuple, list):
                field_names = list_filter
            else:
                field_names = list_filter,
            for field_name in field_names:
                if field_name == self.to:
                    continue
                field = get_field(self.qs.model, field_name)
                form_field_name = '%s%s' % (field_name, self.id)
                if type(field).__name__ in ['DateField', 'DateTimeField']:
                    initial = (self._get_from_request(field_name, None, '_0'), self._get_from_request(field_name, None, '_1'))
                    form.fields[form_field_name] = forms.DateFilterField(label=normalyze(field.verbose_name), initial=initial, required=False)
                else:
                    initial = self._get_from_request(field_name)
                    if type(field).__name__ in ['BooleanField', 'NullBooleanField']:
                        form.fields[form_field_name] = forms.ChoiceField(
                            choices=[['', ''], ['sim', 'Sim'], ['nao', 'Não'], ], label=normalyze(field.verbose_name), initial=initial, required=False)
                    elif hasattr(field, 'choices') and field.choices:
                        form.fields[form_field_name] = forms.ChoiceField(choices=[['', '']] + field.choices, label=normalyze(field.verbose_name), initial=initial, required=False)
                    else:
                        if self.request.user.unit_id and hasattr(field.rel.to, 'unit_ptr_id'):
                            continue
                        if self.request.user.organization_id and hasattr(field.rel.to, 'organization_ptr_id'):
                            continue
                        if not should_filter_or_display(self.request, self.qs.model, field.rel.to):
                            continue

                        if self.original_qs.query.can_filter():
                            pks = self.original_qs.order_by(field_name).values_list(field_name, flat=True).distinct()
                        else:
                            pks = self.original_qs.model.objects.all().order_by(field_name).values_list(field_name, flat=True).distinct()
                        qs = field.rel.to.objects.get_queryset().filter(pk__in=pks)
                        empty_label = ''

                        form.fields[form_field_name] = forms.ModelChoiceField(qs, label=normalyze(field.verbose_name), initial=initial, empty_label=empty_label, required=False)
                    form.fields[form_field_name].widget.attrs['data-placeholder'] = field.verbose_name
                    if initial:
                        label = form.fields[form_field_name].label
                        value = form.fields[form_field_name].clean(initial)
                        if type(form.fields[form_field_name]) == forms.ChoiceField:
                            for x, y in form.fields[form_field_name].choices:
                                if unicode(x) == unicode(value):
                                    value = y
                                    break
                        self.filters.append((label, value))
        return form
    
    def get_response(self):
        export = self.request.GET.get('export', None)
        if export == 'pdf':
            return self._get_pdf_response()
        if export == 'csv':
            return self._get_csv_response(self.get_selected_ids())
        elif export == 'excel':
            return self._get_xls_response(self.get_selected_ids())
        return None

    def get_selected_ids(self):
        ids = self.request.GET.get('ids', None)
        if ids:
            ids = ids.split(',')
            ids = 0 not in ids and ids or None
        return ids

    def add_action(self, label, url, css, icon=None):
        self.paginator_dropdown.add_action(label, url, 'global-action %s' % css, icon, label)

    def add_subset_action(self, label, url, css, icon=None, subset=None):
        if not subset or self.get_tab() == subset:
            if not self.mobile:
                self.subset_dropdown.add_action(label, url, 'subset-action disabled %s' % css, icon, label)

    def add_actions(self):
        export_url = self.request.get_full_path()
        list_csv = get_metadata(self.qs.model, 'list_csv')
        list_xls = get_metadata(self.qs.model, 'list_xls')
        log = get_metadata(self.qs.model, 'log')
        app_label = get_metadata(self.qs.model, 'app_label')
        pdf = get_metadata(self.qs.model, 'pdf')

        if list_csv:
            export_url = '?' in export_url and '%s&export=csv' % export_url or '%s?export=csv' % export_url
            self.add_action('Exportar CSV', export_url, 'ajax', 'fa-table')

        if list_xls:
            export_url = '?' in export_url and '%s&export=excel' % export_url or '%s?export=excel' % export_url
            self.add_action('Exportar Excel', export_url, 'ajax', 'fa-file-excel-o')

        if log:
            log_url = '/log/%s/%s/' % (app_label, self.qs.model.__name__.lower())
            if self.request.user.has_perm('admin.list_log'):
                self.add_action('Visualizar Log', log_url, 'ajax', 'fa-history')

        if pdf:
            pdf_url = '?' in export_url and '%s&export=pdf' % export_url or '%s?export=pdf' % export_url
            self.add_action('Imprimir', pdf_url, 'ajax', 'fa-print')

        subclasses = self.qs.model.__subclasses__()

        if not subclasses and permissions.has_add_permission(self.request, self.qs.model):
            instance = self.qs.model()
            instance.user = self.request.user
            if not hasattr(instance, 'can_add') or instance.can_add():
                add_label = get_metadata(self.qs.model, 'add_label', 'Cadastrar')
                self.add_action(add_label, '/add/%s/%s/' % (app_label, self.qs.model.__name__.lower()), 'ajax', 'fa-plus')

        for subclass in subclasses:
            app = get_metadata(subclass, 'app_label')
            verbose_name = get_metadata(subclass, 'verbose_name')
            cls = subclass.__name__.lower()
            if permissions.has_add_permission(self.request, subclass):
                self.add_action(verbose_name, '/add/%s/%s/' % (app, cls), False, 'fa-plus')

    def get_total(self):
        if self.list_total:
            return self.qs.aggregate(sum=Sum(self.list_total)).get('sum')
        else:
            return None

    def can_show_actions(self):
        return permissions.has_list_permission(self.request, self.qs.model)

    def get_queryset(self, paginate=True):
        queryset = self.qs
        if paginate:
            l = []
            count = queryset.count()
            list_per_page = self._get_list_per_page()
            page_numer = count / list_per_page + (((count % list_per_page) > 0 or count < list_per_page) and 1 or 0)
            current_page = int(self._get_from_request('page', 1))
            start = current_page * list_per_page - list_per_page
            end = start + list_per_page
            queryset = queryset[start:end]
            if page_numer > 1:
                l.append(
                    '<ul class="pagination pagination-xs m-top-none pull-right pagination-split">'
                    '<li class="disabled"><a href="#!"><i class="fa fa-chevron-left"></i></a></li>')
                for i in range(1, page_numer + 1):
                    onclick = "$('#page%s').val(%s);$('#%s').submit();" % (self.id, i, self.id)
                    if i == current_page:
                        css = 'active'
                    else:
                        css = 'waves-effect'
                    l.append('<li class="%s"><a href="javascript:" onclick="%s">%s</a></li>' % (css, onclick, i))
                l.append('<li class="disabled"><a href="#!"><i class="fa fa-chevron-right"></i></a></li></ul>')
            self.pagination = ''.join(l)
        return queryset
    
    def get_q(self):
        return self._get_from_request('q', '')

    def _configure_list_display(self):
        hidden_fields = []
        if not self.list_display:
            self.list_display = list(get_metadata(self.qs.model, 'list_display', []))
        if not self.list_display:
            fields = []
            for field in get_metadata(self.qs.model, 'fields'):
                if not hasattr(field, 'display') or field.display:
                    fields.append(field)
            for field in get_metadata(self.qs.model, 'local_many_to_many'):
                if not hasattr(field, 'display') or field.display:
                    fields.append(field)
            for field in fields[1:6]:
                if not field.name.endswith('_ptr') and not field.name == 'ascii' and not type(field).__name__ == 'TreeIndexField':
                    if not hasattr(field, 'display') or field.display:
                        self.list_display.append(field.name)

        for field_name in self.list_display:
            if '__' in field_name:
                attr = getattr2(self.qs.model, field_name)
            else:
                attr = getattr(self.qs.model, field_name)
            if hasattr(attr, 'field_name'):
                field = getattr(self.qs.model, '_meta').get_field(attr.field_name)
                if hasattr(field, 'display') and not field.display:
                        hidden_fields.append(field_name)

        if self.exclude:
            for field_name in self.exclude:
                if field_name in self.list_display:
                    hidden_fields.append(field_name)

        for field_name in hidden_fields:
            self.list_display.remove(field_name)

    def _configure_column_names(self):
        for lookup in self.list_display:
            hide_field = False
            attr = getattr(self.qs.model, lookup.split('__')[0])
            if hasattr(attr, 'field') and hasattr(attr.field, 'rel') and attr.field.rel and attr.field.rel.to:
                if self.request.user.unit_id and hasattr(attr.field.rel.to, 'unit_ptr_id'):
                    continue
                if self.request.user.organization_id and hasattr(attr.field.rel.to, 'organization_ptr_id'):
                    continue
                if not should_filter_or_display(self.request, self.qs.model, attr.field.rel.to):
                    hide_field = True
            if not hide_field:
                self.column_names.append(get_fiendly_name(self.qs.model, lookup, as_tuple=True))

    def _load_tabs(self):
        from djangoplus.cache import loader
        if self.list_subsets is None:
            list_subsets = loader.subsets[self.qs.model]
        else:
            list_subsets = []
            for subset_name in self.list_subsets:
                for subset in loader.subsets[self.qs.model]:
                    if subset['name'] == subset_name:
                        list_subsets.append(subset)
        create_default_tab = True
        for subset in list_subsets:
            tab_title = subset['title']
            tab_function = subset['function']
            tab_can_view = subset['can_view']
            tab_name = subset['name']
            tab_order = subset['order']
            tab_active = False
            if permissions.check_group_or_permission(self.request, tab_can_view):
                tab_qs = tab_function()
                tab_qs = tab_qs.all(self.request.user)
                tab_active = self.current_tab == tab_name
                self.tabs.append([tab_name, tab_title, tab_qs, tab_active, tab_order])
            if tab_name == 'all':
                create_default_tab = False
            if tab_active:
                self.qs = tab_qs
                self.drop_down = ModelDropDown(self.request, self.qs.model)
        self.tabs = sorted(self.tabs, key=lambda k: k[4])
        if self.list_subsets is None and create_default_tab:
            tab_title = get_metadata(self.qs.model, 'verbose_female') and 'Todas' or 'Todos'
            tab_qs = self.original_qs
            tab_active = self.current_tab == 'all'
            tab_order = 0
            self.tabs.insert(0, ['', tab_title, tab_qs, tab_active, tab_order])
        if not self.current_tab and self.tabs:
            self.tabs[0][3] = True
            self.qs = self.tabs[0][2]

    def _get_from_request(self, param_name, default='', suffix=''):
        key = '%s%s%s' % (param_name, self.id, suffix)
        value = self.request.GET.get(unicode(self.id)) and self.request.GET.get(key) or default
        return value

    def _get_order_by(self):
        return self._get_from_request('order_by', '')

    def _get_page(self):
        return self._get_from_request('page', 1)

    def _get_list_per_page(self):
        return get_metadata(self.qs.model, 'list_per_page', self.list_per_page)

    def _filter_queryset(self, qs):
        distinct = False
        queryset = None
        search_fields = self.get_search_fields()
        q = self.get_q()
        if q:
            for i, search_field in enumerate(search_fields):
                if i == 0:
                    queryset = qs.filter(**{'%s__icontains' % search_field: q})
                else:
                    queryset = queryset | qs.filter(**{'%s__icontains' % search_field: q})
        else:
            queryset = qs
        for field_name in self.get_list_filter():
            field = get_field(queryset.model, field_name)
            if type(field).__name__ == 'DateField':
                filter_value = self._get_from_request(field_name, None, '_0')
                if filter_value:
                    date, month, year = filter_value.split('/')
                    filter_value = '%s-%s-%s' % (year, month, date)
                    queryset = queryset.filter(**{'%s__gte' % field_name: filter_value})
                filter_value = self._get_from_request(field_name, None, '_1')
                if filter_value:
                    date, month, year = filter_value.split('/')
                    filter_value = '%s-%s-%s' % (year, month, date)
                    queryset = queryset.filter(**{'%s__lte' % field_name: filter_value})
            elif type(field).__name__ in ['BooleanField', 'NullBooleanField']:
                filter_value = self._get_from_request(field_name)
                if filter_value:
                    filter_value = filter_value == 'sim'
                    queryset = queryset.filter(**{field_name: filter_value})
            else:
                filter_value = self._get_from_request(field_name)
                if filter_value:
                    queryset = queryset.filter(**{field_name: filter_value})
                if type(field).__name__ == 'ManyToManyField':
                    distinct = True
        order_by = self._get_from_request('order_by')

        tree_index_field = hasattr(self.qs.model, 'get_tree_index_field') and self.qs.model().get_tree_index_field() or None
        if tree_index_field:
            queryset = queryset.order_by(tree_index_field.name)
        else:
            if order_by:
                queryset = queryset.order_by(order_by.replace('0', ''))
            else:
                order_by = get_metadata(self.qs.model, 'order_by', iterable=True)
                try:
                    queryset = queryset.order_by(*order_by)
                except AssertionError:
                    # if the querycet was sliced
                    pass
        if distinct:
            queryset = queryset.distinct()
        return queryset

    def _get_csv_response(self, ids=()):
        list_csv = get_metadata(self.qs.model, 'list_csv')
        qs = self.get_queryset(False)
        if ids:
            qs = qs.filter(id__in=ids)
        return CsvResponse(tolist(qs, list_display=list_csv))

    def _get_xls_response(self, ids=()):
        list_xls = get_metadata(self.qs.model, 'list_xls')
        qs = self.get_queryset(False)
        if ids:
            qs = qs.filter(id__in=ids)
        return XlsResponse([(u'Dados', tolist(qs, list_display=list_xls))])

    def _get_pdf_response(self):
        self.as_pdf = True
        landscape = len(self.list_display) > 4
        return ReportResponse(self.title, self.request, [self], landscape)

    def __unicode__(self):
        return self.render('paginator.html')