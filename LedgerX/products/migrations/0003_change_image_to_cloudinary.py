from django.db import migrations
import cloudinary.models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '000X_previous_migration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image',
            field=cloudinary.models.CloudinaryField(
                'product_image',
                blank=True,
                null=True,
                max_length=255
            ),
        ),
    ]
