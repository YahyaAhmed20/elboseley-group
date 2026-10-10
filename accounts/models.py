# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN  = 'admin',  'مدير'
        KEEPER = 'keeper', 'أمين مخزن'
        VIEWER = 'viewer', 'مشاهدة فقط'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)

    @property
    def can_add_item(self):   return self.role == self.Role.ADMIN
    @property
    def can_move(self):       return self.role in (self.Role.ADMIN, self.Role.KEEPER)
    @property
    def can_manage_users(self): return self.role == self.Role.ADMIN

    @property
    def can_manage_employees(self): return self.role == self.Role.ADMIN
    @property
    def can_manage_customers(self): return self.role == self.Role.ADMIN
    @property
    def can_manage_operations(self): return self.role == self.Role.ADMIN