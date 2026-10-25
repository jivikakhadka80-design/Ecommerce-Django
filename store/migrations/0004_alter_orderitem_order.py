import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Records ``related_name='items'`` on OrderItem.order, which the model
    already declares but no earlier migration captured."""

    dependencies = [
        ('store', '0003_alter_cartitem_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='items',
                to='store.order'),
        ),
    ]
