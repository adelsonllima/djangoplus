# -*- coding: utf-8 -*-
from django.apps import apps
from django.conf import settings
from djangoplus.utils.metadata import get_metadata, get_scope

initialized = False

# user interface
views = []
widgets = []
subset_widgets = []
card_panel_models = []
icon_panel_models = []
subsets = dict()

# roles
role_models = dict()
role_model_names = []
abstract_role_models = dict()
abstract_role_model_names = dict()

# actions
actions = dict()
class_actions = dict()
fieldset_actions = dict()
subset_actions = dict()

# documentation
workflows = dict()
class_diagrams = dict()
composition_fields = dict()
composition_relations = dict()

# access scope
organization_model = None
unit_model = None
signup_model = None
permissions_by_scope = dict()

formatters = dict()

if not initialized:
    initialized = True
    for model in apps.get_models():
        model_name = model.__name__.lower()
        app_label = get_metadata(model, 'app_label')
        add_shortcut = get_metadata(model, 'add_shortcut')
        list_shortcut = get_metadata(model, 'list_shortcut')
        verbose_name = get_metadata(model, 'verbose_name')
        verbose_name_plural = get_metadata(model, 'verbose_name_plural')
        list_menu = get_metadata(model, 'list_menu')
        role_signup = get_metadata(model, 'role_signup', False)

        field_names = []
        for field in get_metadata(model, 'get_fields'):
            field_names.append(field.name)
            if hasattr(field, 'composition') and field.composition:
                composition_fields[model] = field.name
                if field.rel.to not in composition_relations:
                    composition_relations[field.rel.to] = []
                if model not in composition_relations[field.rel.to]:
                    composition_relations[field.rel.to].append(model)

        if model not in subsets:
            subsets[model] = []
        if model not in subset_actions:
            subset_actions[model] = dict()
        if model not in actions:
            actions[model] = dict()
        if model not in class_actions:
            class_actions[model] = dict()
        if model not in fieldset_actions:
            fieldset_actions[model] = dict()

        if role_signup:
            signup_model = model

        # indexing organization model
        if hasattr(model, 'organization_ptr_id'):
            organization_model = model

        # indexing unit model
        if hasattr(model, 'unit_ptr_id'):
            unit_model = model

        # indexing shortcuts
        if add_shortcut:
            icon_panel_models.append((model, add_shortcut))
        if list_shortcut:
            card_panel_models.append((model, list_shortcut))

        # indexing the views generated from model classes
        url = '/list/%s/%s/' % (app_label, model_name)
        icon = None
        if list_menu and model not in composition_fields:
            if type(list_menu) == tuple:
                menu, icon = list_menu
            else:
                menu, icon = list_menu, get_metadata(model, 'icon')
            permission = u'%s.list_%s' % (app_label, model_name)
            # if issubclass(model, Model):
            item = dict(url=url, can_view=permission, menu=menu, icon=icon, add_shortcut=False)
            views.append(item)

        # indexing the subsets defined in the manager classes

        for attr_name in dir(model.objects.get_queryset()):
            attr = getattr(model.objects.get_queryset(), attr_name)
            if hasattr(attr, '_metadata'):
                metadata_type = attr._metadata['%s:type' % attr_name]
                if metadata_type == 'subset':
                    subset_title = attr._metadata['%s:title' % attr_name]
                    subset_name = attr._metadata['%s:name' % attr_name]
                    subset_alert = attr._metadata['%s:alert' % attr_name]
                    subset_notify = attr._metadata['%s:notify' % attr_name]
                    subset_can_view = attr._metadata['%s:can_view' % attr_name]
                    subset_order = attr._metadata['%s:order' % attr_name]
                    subset_menu = attr._metadata['%s:menu' % attr_name]
                    subset_url = u'%s%s/' % (url, attr.im_func.func_name)

                    item = dict(title=subset_title, name=attr_name, function=attr, url=subset_url, can_view=subset_can_view, menu=subset_menu, icon=icon, alert=subset_alert, notify=subset_notify, actions=subset_actions, order=subset_order)
                    subsets[model].append(item)


                else:
                    widget_title = attr._metadata['%s:verbose_name' % attr_name]
                    widget_can_view = attr._metadata['%s:can_view' % attr_name]
                    widget_position = attr._metadata['%s:position' % attr_name]
                    widget_formatter = attr._metadata['%s:formatter' % attr_name]
                    widget = dict(title=widget_title, model=model, function=attr_name, can_view=widget_can_view, position=widget_position, formatter=widget_formatter)
                    subset_widgets.append(widget)

        # indexing the actions refered in fieldsets
        if hasattr(model, 'fieldsets'):
            for title, info in model.fieldsets:
                if title not in fieldset_actions[model]:
                    fieldset_actions[model][title] = []
                for action_name in info.get('actions', []):
                    fieldset_actions[model][title].append(action_name)

        # indexing the actions defined in models
        for attr in dir(model):
            if attr[0] != '_' and attr not in field_names:
                function = getattr(model, attr)
                if hasattr(function, '_action'):
                    action = getattr(function, '_action')
                    action_group = action['group']

                    action_can_execute = action['can_execute']
                    action_title = action['title']
                    action_workflow = action['sequence']
                    action_menu = action['menu']
                    action_inline = action['inline']
                    view_name = action['view_name']
                    if action_group not in actions[model]:
                        actions[model][action_group] = dict()
                    actions[model][action_group][view_name] = action
                    if action_inline:
                        action_subset = action_inline is not True and action_inline or None
                        if action_subset not in subset_actions[model]:
                            subset_actions[model][action_subset] = []
                        subset_actions[model][action_subset].append(attr)
                    if action_workflow:
                        role = action_can_execute and action_can_execute[0] or u'Superusuário'
                        workflows[action_workflow] = dict(activity=action_title, role=role, model=verbose_name)
                    if action_menu:
                        url = '/action/%s/%s/%s/' % (get_metadata(model, 'app_label'), model.__name__.lower(), attr)
                        action_view = dict(title=action_title, function=None, url=url, can_view=action_can_execute, menu=action_menu, icon=None,
                              style='ajax', add_shortcut=False, doc=function.__doc__, sequence=None)
                        views.append(action_view)

        # indexing the actions defined in managers
        for attr_name in dir(model.objects.get_queryset()):
            if not attr_name[0] == '_':
                attr = getattr(model.objects.get_queryset(), attr_name)
                if hasattr(attr, '_action'):
                    action = getattr(attr, '_action')
                    action_group = action['group']
                    view_name = action['view_name']
                    action_subset = action['inline']
                    if action_group not in class_actions[model]:
                        class_actions[model][action_group] = dict()
                    class_actions[model][action_group][view_name] = action

                    if action_subset not in subset_actions[model]:
                        subset_actions[model][action_subset] = []
                    subset_actions[model][action_subset].append(view_name)

    # indexing the actions, views and widgets in views module
    for app_label in settings.INSTALLED_APPS:
            try:
                module = __import__('%s.formatters' % app_label, fromlist=app_label.split('.'))
                for attr_name in dir(module):
                    module_attr = getattr(module, attr_name)
                    if callable(module_attr):
                        formatters[attr_name] = module_attr
            except ImportError:
                pass

            try:
                module = __import__('%s.views' % app_label, fromlist=app_label.split('.'))
                for attr_name in dir(module):
                    function = getattr(module, attr_name)
                    # indexing the actions
                    if hasattr(function, '_action'):
                        action = function._action
                        action_group = action['group']
                        action_model = action['model']
                        action_function = action['function']
                        action_name = action['view_name']
                        action_title = action['title']
                        action_workflow = action['sequence']
                        action_can_execute = action['can_execute']
                        action_menu = action['menu']
                        if action_workflow:
                            role = action_can_execute and action_can_execute[0] or u'Superusuário'
                            action_model_verbose_name = get_metadata(action_model, 'verbose_name')
                            workflows[action_workflow] = dict(activity=action_title, role=role, model=action_model_verbose_name)
                        if action_function.func_code.co_argcount > 1:
                            if action_group not in actions[action_model]:
                                actions[action_model][action_group] = dict()
                            actions[action_model][action_group][action_name] = action
                        else:
                            if action_model not in class_actions:
                                class_actions[action_model] = dict()
                            if action_group not in class_actions[action_model]:
                                class_actions[action_model][action_group] = dict()
                            class_actions[action_model][action_group][action_name] = action
                    # indexing the views
                    elif hasattr(function, '_view'):
                        views.append(function._view)
                        view_title = function._view['title']
                        view_workflow = function._view['sequence']
                        view_can_view = function._view['can_view']
                        if view_workflow:
                            role = view_can_view and view_can_view[0] or u'Superusuário'
                            workflows[view_workflow] = dict(activity=view_title, role=role, model=None)
                    # indexing the widgets
                    elif hasattr(function, '_widget'):
                        widgets.append(function._widget)
            except ImportError:
                pass

    for model in apps.get_models():
        app_label = get_metadata(model, 'app_label')
        verbose_name = get_metadata(model, 'verbose_name')
        role_username = get_metadata(model, 'role_username')
        add_label = get_metadata(model, 'add_label', None)
        workflow = get_metadata(model, 'sequence', 0)
        diagram_classes = get_metadata(model, 'class_diagram', None)

        # indexing role models
        if role_username:
            role_models[model] = dict(username_field=role_username, scope=get_scope(model, organization_model, unit_model), name=verbose_name)
        for subclass in model.__subclasses__():
            subclass_role_username = get_metadata(subclass, 'role_username')
            if subclass_role_username:
                subclass_verbose_name = get_metadata(subclass, 'verbose_name')
                role_models[subclass] = dict(username_field=subclass_role_username, scope=get_scope(subclass, organization_model, unit_model), name=subclass_verbose_name)
                if model not in abstract_role_models:
                    abstract_role_models[model] = []
                    abstract_role_model_names[verbose_name] = []
                abstract_role_models[model].append(subclass)
                abstract_role_model_names[verbose_name].append(subclass_verbose_name)

        permission_by_scope = dict()
        for scope in ('role', 'unit', 'organization'):
            for permission_name in ('edit', 'add', 'delete', 'list'):
                permission_key = '%s_by_%s' % (permission_name, scope)
                for group_name in get_metadata(model, 'can_%s' % permission_key, (), iterable=True):
                    if permission_key not in permission_by_scope:
                        permission_by_scope[permission_key] = []
                    if group_name in abstract_role_model_names:
                        for concrete_group_name in abstract_role_model_names[group_name]:
                            permission_by_scope[permission_key].append(concrete_group_name)
                    else:
                        permission_by_scope[permission_key].append(group_name)
            for group_name in get_metadata(model, 'can_admin_by_%s' % scope, (), iterable=True):
                for permission_name in ('edit', 'add', 'delete', 'list'):
                    permission_key = '%s_by_%s' % (permission_name, scope)
                    if permission_key not in permission_by_scope:
                        permission_by_scope[permission_key] = []
                    if group_name not in permission_by_scope[permission_key]:
                        if group_name in abstract_role_model_names:
                            for concrete_group_name in abstract_role_model_names[group_name]:
                                permission_by_scope[permission_key].append(concrete_group_name)
                        else:
                            permission_by_scope[permission_key].append(group_name)

        for permission_name in ('edit', 'add', 'delete', 'list'):
            permission_key = permission_name
            for group_name in get_metadata(model, 'can_%s' % permission_name, (), iterable=True):
                if permission_key not in permission_by_scope:
                    permission_by_scope[permission_key] = []
                if group_name not in permission_by_scope[permission_key]:
                    permission_by_scope[permission_key].append(group_name)
        for group_name in get_metadata(model, 'can_admin', (), iterable=True):
            for permission_name in ('edit', 'add', 'delete', 'list'):
                permission_key = permission_name
                if permission_key not in permission_by_scope:
                    permission_by_scope[permission_key] = []
                if group_name not in permission_by_scope[permission_key]:
                    permission_by_scope[permission_key].append(group_name)

        for actions_dict in (actions, class_actions):
            for category in actions_dict[model]:
                for key in actions_dict[model][category].keys():
                    name = actions_dict[model][category][key]['title']
                    view_name = actions_dict[model][category][key]['view_name']
                    can_execute = []
                    for scope in ('', 'role', 'unit', 'organization'):
                        scope = scope and '_by_%s' % scope or scope
                        for group_name in actions_dict[model][category][key].get('can_execute%s' % scope) or ():
                            permission_key = '%s%s' % (view_name, scope)
                            if permission_key not in permission_by_scope:
                                permission_by_scope[permission_key] = []
                            permission_by_scope[permission_key].append(group_name)

        if permission_by_scope:
            permissions_by_scope[model] = permission_by_scope

        if workflow:
            role = permission_by_scope.get('add') and permission_by_scope.get('add')[0] or None
            if not role:
                role = permission_by_scope.get('add_by_role') and permission_by_scope.get('add_by_role')[0] or None
            if not role:
                role = permission_by_scope.get('add_by_unit') and permission_by_scope.get('add_by_unit')[0] or None
            if not role:
                role = permission_by_scope.get('add_by_organization') and permission_by_scope.get('add_by_organization')[0] or None
            if not role:
                role = u'Superusuário'

            if model in composition_fields:
                related_model = getattr(model, composition_fields[model]).field.rel.to
                related_verbose_name = get_metadata(related_model, 'verbose_name')
                related_add_label = get_metadata(model, 'add_label')
                if related_add_label:
                    activity = u'%s em %s' % (related_add_label, related_verbose_name)
                else:
                    activity = u'Adicionar %s em %s' % (verbose_name, related_verbose_name)
                workflows[workflow] = dict(activity=activity, role=role, model=None)
            else:
                if add_label:
                    activity = add_label
                else:
                    activity = u'%s %s' % (u'Cadastrar', verbose_name)
                workflows[workflow] = dict(activity=activity, role=role, model=None)

        if diagram_classes is not None:
            class_diagrams[verbose_name] = [model]
            if type(diagram_classes) == bool and diagram_classes:
                for field in model._meta.get_fields():
                    if hasattr(field, 'rel') and hasattr(field.rel, 'to') and field.rel.to:
                        if field.rel.to not in class_diagrams[verbose_name]:
                            class_diagrams[verbose_name].append(field.rel.to)
            else:
                for model_name in diagram_classes:
                    try:
                        extra_model = apps.get_model(app_label, model_name)
                    except LookupError:
                        for extra_model in apps.get_models():
                            if extra_model.__name__.lower() == model_name:
                                break
                    if extra_model not in class_diagrams[verbose_name]:
                        class_diagrams[verbose_name].append(extra_model)

    keys = workflows.keys()
    keys.sort()
    l = []
    for key in keys:
        l.append(workflows[key])
    workflows = l
