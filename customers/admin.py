from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'personal_number', 'car_number', 'amount', 'follow_up_enabled', 'follow_up_date', 'reminder_sent_at')
    list_filter = ('follow_up_enabled',)
    search_fields = ('name', 'personal_number', 'car_number', 'note')
