"""
Data migration to populate unique UUID values for existing orders,
then add a unique constraint.
"""
from django.db import migrations, models
import uuid


def populate_uuids(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    seen = set()
    for order in Order.objects.all():
        if not order.uuid or order.uuid in seen:
            order.uuid = uuid.uuid4()
            while order.uuid in seen:
                order.uuid = uuid.uuid4()
            order.save(update_fields=["uuid"])
        seen.add(order.uuid)


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_pos_order_extensions"),
    ]

    operations = [
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
    ]
