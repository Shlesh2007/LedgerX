from django.db import migrations
import cloudinary.models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_product_image'),
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
