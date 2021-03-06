# -*- coding: utf-8 -*-
import re
import datetime
import unicodedata
from decimal import Decimal
from django.utils.safestring import mark_safe
from django.db.models.fields.files import FieldFile, ImageFieldFile as DjangoImageFieldFile


def normalyze(nome):
    nome = unicode(nome)

    if nome.isupper():
        return nome

    ponto = '\.'
    ponto_espaco = '. '
    espaco = ' '
    regex_multiplos_espacos = '\s+'
    regex_numero_romano = '^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'

    nome = re.sub(ponto, ponto_espaco, nome)  # colocando espaço após nomes abreviados
    nome = re.sub(regex_multiplos_espacos, espaco, nome)  # retirando espaços múltiplos
    nome = nome.title()  # alterando os nomes para CamelCase
    partes_nome = nome.split(espaco)  # separando as palavras numa lista
    excecoes = [
        'de', 'di', 'do', 'da', 'dos', 'das', 'dello', 'della', 'dalla',
        'dal', 'del', 'e', 'em', 'na', 'no', 'nas', 'nos', 'van', 'von', 'y', 'para', 'pela', 'pelo', 'por',
    ]

    resultado = []

    for palavra in partes_nome:
        if palavra.lower() in excecoes:
            resultado.append(palavra.lower())
        elif re.match(regex_numero_romano, palavra.upper()):
            resultado.append(palavra.upper())
        else:
            resultado.append(palavra)

    nome = espaco.join(resultado)
    return nome


def format_bool(value):
    return value and u'<span class="label label-success">Sim</span>' or u'<span class="label label-danger">Não</span>'


def format_value(value, html=True):
    from djangoplus.db.models.fields import ImageFieldFile
    if value is None or value == '' or value == ():
        return '-'
    elif type(value) == str:
        return value
    elif isinstance(value, Decimal):
        if hasattr(value, 'decimal3'):
            return format_decimal3(value)
        return format_decimal(value)
    elif isinstance(value, ImageFieldFile) or isinstance(value, DjangoImageFieldFile):
        value = unicode(value)
        url = u'/static/' in value and value or '/media/%s' % value
        return html and mark_safe('<img width="50px" class="materialboxed" src="%s"/>' % url) or value
    elif isinstance(value, FieldFile):
        value = unicode(value)
        url = u'/static/' in value and value or '/media/%s' % value
        file_name = value.split('/')[-1]
        if url.lower().endswith('.pdf'):
            return html and mark_safe(
                '<a class="ajax pdf" href="%s">%s</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="%s"><i class="mdi-file-file-download"></i></a>' % (
                url, file_name, url)) or file_name
        else:
            return html and mark_safe('<a target="_blank" href="%s">%s</a>' % (url, file_name)) or url
    elif isinstance(value, bool):
        return value and u'Sim' or u'Não'
    elif value.__class__ == datetime.date:
        return value.strftime('%d/%m/%Y')
    elif value.__class__ == datetime.datetime:
        return value.strftime('%d/%m/%Y %H:%M')
    elif type(value).__name__ in ('QuerySet',) or type(value) == list:
        if html:
            l = [u'<ul>']
            for obj in value:
                l.append(u'<li>%s</li>' % obj)
            l.append(u'</ul>')
            return mark_safe(u''.join(l))
        else:
            l = []
            for obj in value:
                l.append(unicode(obj))
            return u', '.join(l)
    elif isinstance(value, tuple):
        return u'%s %s' % (value[0], value[1])
    else:
        return unicode(value)


def split_thousands(value, sep='.'):
    if not isinstance(value, basestring):
        value = str(value)
    negativo = False
    if '-' in value:
        value = value.replace('-', '')
        negativo = True
    if len(value) <= 3:
        if negativo:
            return '- ' + value
        else:
            return value
    if negativo:
        return '- ' + split_thousands(value[:-3], sep) + sep + value[-3:]
    else:
        return split_thousands(value[:-3], sep) + sep + value[-3:]


def format_decimal(value):
    value = str(value)
    if '.' in value:
        reais, centavos = value.split('.')
        if len(centavos) == 1:
            centavos = '%s0' % centavos
        elif len(centavos) > 2:
            centavos = centavos[0:2]
    else:
        reais = value
        centavos = '00'
    reais = split_thousands(reais)
    return reais + ',' + centavos


def format_decimal3(value):
    value = str(value)
    if '.' in value:
        reais, centavos = value.split('.')
        centavos = '%s000' % centavos
        if len(centavos) == 1:
            centavos = '%s0' % centavos
        elif len(centavos) > 3:
            centavos = centavos[0:3]
    else:
        reais = value
        centavos = '000'
    reais = split_thousands(reais)
    return reais + ',' + centavos


def to_ascii(txt, codif='utf-8'):
    if not isinstance(txt, basestring):
        txt = unicode(txt)
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return unicodedata.normalize('NFKD', txt.decode(codif)).encode('ASCII', 'ignore')