from django.contrib import admin
from .models import Employee, EmployeePayroll, PayrollMonth, PayrollTransaction

admin.site.register(Employee)
admin.site.register(PayrollMonth)
admin.site.register(EmployeePayroll)
admin.site.register(PayrollTransaction)
