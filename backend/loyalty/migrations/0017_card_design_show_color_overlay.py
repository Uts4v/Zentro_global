from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loyalty", "0016_customermerchantwallet_membership_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="merchantmembershipcarddesign",
            name="show_color_overlay",
            field=models.BooleanField(default=True),
        ),
    ]
