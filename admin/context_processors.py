# -*- coding: utf-8 -*-
import copy
from django.conf import settings
from djangoplus.cache import loader
from djangoplus.ui.components.menu import Menu
from djangoplus.admin.models import Settings
from djangoplus.utils import permissions
from djangoplus.utils.metadata import get_metadata


def context_processor(request):
    app_settings = Settings.default()
    alerts = []
    menu = None

    if request.user.is_authenticated:
        menu = Menu(request, app_settings)
        menu.load()

        for model in loader.subsets:
            icon = get_metadata(model, 'icon', u'fa-warning')
            title = get_metadata(model, 'verbose_name_plural')
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            for item in loader.subsets[model]:
                can_view = item['can_view']
                alert = item['alert']
                if alert and permissions.check_group_or_permission(request, can_view):
                    attr_name = item['function'].im_func.func_name
                    qs = model.objects.all(request.user)
                    qs = getattr(qs, attr_name)()
                    count = qs.count()
                    if count:
                        url = '/list/%s/%s/%s/' % (app_label, model_name, attr_name)
                        item = dict(title=title, description=item['title'], count=count, url=url, icon=icon)
                        alerts.append(item)

    return dict(
        js_files=settings.EXTRA_JS,
        css_files=settings.EXTRA_CSS,
        settings=app_settings,
        menu=menu,
        alerts=alerts
    )
