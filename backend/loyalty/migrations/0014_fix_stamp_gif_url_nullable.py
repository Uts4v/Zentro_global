from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loyalty', '0013_add_stamp_gif_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='merchantpunchcard',
            name='stamp_gif_url',
            field=models.URLField(blank=True, default='', null=True, help_text='Optional GIF URL to use instead of emoji stamp'),
        ),
    ]
