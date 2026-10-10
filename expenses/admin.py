from django.contrib import admin
from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "beneficiary",
        "category",
        "amount",
        "expense_date",
        "created_by",
    )
    list_filter = ("category", "expense_date")
    search_fields = (
        "beneficiary__name",
        "category__name",
        "note",
    )