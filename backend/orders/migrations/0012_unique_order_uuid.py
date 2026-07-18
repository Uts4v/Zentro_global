"""
Add unique constraint to Order.uuid after all rows have unique values.
"""
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_populate_order_uuids"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
    ]
