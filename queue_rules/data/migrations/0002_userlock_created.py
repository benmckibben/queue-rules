# Generated by Django 3.1 on 2020-09-04 19:09

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0001_squashed_0004_auto_20200823_1905"),
    ]

    operations = [
        migrations.AddField(
            model_name="userlock",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True,
                default=datetime.datetime(2020, 9, 4, 19, 9, 39, 855666, tzinfo=utc),
            ),
            preserve_default=False,
        ),
    ]