# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-10-05 15:36
from __future__ import unicode_literals

from django.db import migrations
import djangoplus.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('admin', '0004_auto_20161001_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='settings',
            name='theme',
            field=djangoplus.db.models.fields.CharField(choices=[[b'skin-7', b'skin-7'], [b'skin-6', b'skin-6'], [b'skin-5', b'skin-5'], [b'skin-4', b'skin-4'], [b'skin-3', b'skin-3'], [b'skin-2', b'skin-2'], [b'skin-1', b'skin-1']], default=b'skin-6', max_length=255, verbose_name='Tema'),
        ),
    ]