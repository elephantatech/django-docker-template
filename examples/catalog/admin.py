from django.contrib import admin

from .models import Product, Stock


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "price", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "sku")
    inlines = [StockInline]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "last_restocked")
    list_filter = ("warehouse",)
    search_fields = ("product__name", "warehouse")
