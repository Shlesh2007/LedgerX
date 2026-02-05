from django.db import models
from accounts.models import Shop

class Product(models.Model):
    """
    Product available in a specific shop.
    No global products exist.
    """

    # Owner shop
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products'
    )

    # Product info
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, blank=True, null=True)

    # Default selling price
    default_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Inventory
    stock_quantity = models.PositiveIntegerField()
    low_stock_threshold = models.PositiveIntegerField(default=5)

    # Soft delete
    is_active = models.BooleanField(default=True)

    image = CloudinaryField(
        'product_image',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.shop.shop_name})"
