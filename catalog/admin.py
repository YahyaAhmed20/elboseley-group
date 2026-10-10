from django.contrib import admin
from .models import ItemType, Brand, Unit, Item


@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    list_display  = ('name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display  = ('name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)          # ← كان ناقصاً


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display  = ('name', 'short')
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display        = ('name', 'type', 'brand', 'unit', 'min_qty', 'cost', 'current_qty_display')
    list_filter         = ('type', 'brand', 'is_active')
    search_fields       = ('name', 'brand__name')
    autocomplete_fields = ('brand',)

    @admin.display(description='الرصيد')
    def current_qty_display(self, obj):
        return obj.current_qty