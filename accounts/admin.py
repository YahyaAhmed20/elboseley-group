from django.contrib import admin

# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as Base
from .models import User

@admin.register(User)
class UserAdmin(Base):
    list_display = ('username','first_name','role','is_active')
    list_editable = ('role','is_active')