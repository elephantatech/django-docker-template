from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    quantity = models.PositiveIntegerField(default=0)
    warehouse = models.CharField(max_length=100)
    last_restocked = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("product", "warehouse")

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse}: {self.quantity}"
