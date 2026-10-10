from datetime import date

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .models import Customer, add_months


class CustomerReminderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass', role=User.Role.ADMIN)

    def test_add_months_handles_month_end(self):
        self.assertEqual(add_months(date(2026, 8, 31), 6), date(2027, 2, 28))

    def test_follow_up_is_six_months_from_creation(self):
        customer = Customer.objects.create(
            name='محمد', personal_number='123', car_number='س ص 1234', amount='500',
            created_by=self.user,
        )
        customer.set_follow_up(True)
        customer.save(update_fields=['follow_up_enabled', 'follow_up_date', 'reminder_sent_at', 'updated_at'])
        self.assertEqual(customer.follow_up_date, add_months(customer.created_at.date(), 6))

    def test_disabled_follow_up_has_no_date(self):
        customer = Customer.objects.create(
            name='محمد', personal_number='123', car_number='س ص 1234', amount='500',
            created_by=self.user,
        )
        customer.set_follow_up(False)
        customer.save()
        self.assertFalse(customer.follow_up_enabled)
        self.assertIsNone(customer.follow_up_date)
