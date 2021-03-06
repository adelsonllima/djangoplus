# -*- coding: utf-8 -*-
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
import tempfile
import json
import os


def mobile(request):
    for device in ['iphone', 'android']:
        if device in request.META.get('HTTP_USER_AGENT', '').lower():
            return True
    return False


class XlsResponse(HttpResponse):
    def __init__(self, data, name='Listagem'):
        import xlwt
        import StringIO
        output = StringIO.StringIO()
        wb = xlwt.Workbook(encoding='iso8859-1')
        for title, rows in data:
            sheet = wb.add_sheet(title)
            for row_idx, row in enumerate(rows):
                for col_idx, label in enumerate(row):
                    sheet.write(row_idx, col_idx, label=label)
        wb.save(output)
        HttpResponse.__init__(self, content=output.getvalue(), content_type='application/vnd.ms-excel')
        self['Content-Disposition'] = 'attachment; filename=%s.xls' % name


class CsvResponse(HttpResponse):
    def __init__(self, rows, name='Listagem'):
        import unicodecsv
        import StringIO
        output = StringIO.StringIO()
        delimiter = os.sep == '/' and ',' or ';'
        writer = unicodecsv.writer(output, delimiter=delimiter, encoding='iso8859-1')
        for row in rows:
            writer.writerow(row)
        HttpResponse.__init__(self, content=output.getvalue(), content_type='application/csv')
        self['Content-Disposition'] = 'attachment; filename=%s.xls' % name


class ZipResponse(HttpResponse):
    def __init__(self, file_path):
        content = open(file_path)
        HttpResponse.__init__(self, content=content, content_type='application/zip')
        self['Content-Disposition'] = 'attachment; filename=%s' % file_path.split(os.sep)[-1]


class JsonResponse(HttpResponse):
    def __init__(self, data):
        content = json.dumps(data)
        HttpResponse.__init__(self, content=content, content_type='application/json')


class PdfResponse(HttpResponse):

    def __init__(self, html, landscape=False):
        from xhtml2pdf import pisa

        def link_callback(uri, rel):
            s = '%s/%s' % (settings.MEDIA_ROOT, uri)
            return s

        tmp = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
        file_name = tmp.name
        if landscape:
            html = html.replace('a4 portrait', 'a4 landscape')
            html = html.replace('logo_if_portrait', 'logo_if_landscape')
        out = pisa.CreatePDF(html, tmp, link_callback=link_callback)
        out.dest.close()
        tmp = file(file_name, "rb")
        str_bytes = tmp.read()
        os.unlink(file_name)
        HttpResponse.__init__(self, str_bytes, content_type='application/pdf')


class ReportResponse(PdfResponse):
    def __init__(self, title, request, objects, landscape=False):
        html = render_to_string(['report.html'], dict(objects=objects, title=title), request=request)
        PdfResponse.__init__(self, html, landscape)