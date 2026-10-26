from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import Account, JournalEntry, JournalLine
from finance.services import (
    create_journal_entry,
    ensure_default_accounts,
    reverse_journal_entry,
)


class JournalEntryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="accounting_test_user",
            password="test-password",
            role="admin",
        )
        self.cash = Account.objects.create(
            code="1001",
            name="الخزينة",
            account_type=Account.AccountType.ASSET,
        )
        self.revenue = Account.objects.create(
            code="4001",
            name="إيرادات الخدمات",
            account_type=Account.AccountType.REVENUE,
        )

    def valid_lines(self):
        return [
            {
                "account_id": self.cash.pk,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
            },
            {
                "account_id": self.revenue.pk,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
            },
        ]

    def test_creates_balanced_posted_entry(self):
        entry = create_journal_entry(
            entry_number="TEST-0001",
            entry_date="2026-10-26",
            description="اختبار إيراد",
            lines=self.valid_lines(),
            user=self.user,
        )

        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.lines.count(), 2)

        debit = sum(line.debit for line in entry.lines.all())
        credit = sum(line.credit for line in entry.lines.all())

        self.assertEqual(debit, Decimal("100.00"))
        self.assertEqual(credit, Decimal("100.00"))

    def test_rejects_unbalanced_entry(self):
        lines = self.valid_lines()
        lines[1]["credit"] = Decimal("90.00")

        with self.assertRaises(ValidationError):
            create_journal_entry(
                entry_number="TEST-0002",
                entry_date="2026-10-26",
                description="قيد غير متوازن",
                lines=lines,
                user=self.user,
            )

        self.assertFalse(
            JournalEntry.objects.filter(entry_number="TEST-0002").exists()
        )

    def test_rejects_duplicate_entry_number(self):
        create_journal_entry(
            entry_number="TEST-0003",
            entry_date="2026-10-26",
            description="قيد تجريبي",
            lines=self.valid_lines(),
            user=self.user,
        )

        with self.assertRaises(Exception):
            create_journal_entry(
                entry_number="TEST-0003",
                entry_date="2026-10-26",
                description="قيد مكرر",
                lines=self.valid_lines(),
                user=self.user,
            )

    def test_default_accounts_are_created_idempotently(self):
        first_result = ensure_default_accounts()
        second_result = ensure_default_accounts()

        self.assertEqual(len(first_result), 5)
        self.assertEqual(len(second_result), 5)

        self.assertEqual(
            Account.objects.filter(is_system=True).count(),
            5,
        )

        self.assertEqual(
            first_result["1000"].pk,
            second_result["1000"].pk,
        )

    def test_reverses_posted_entry_without_changing_original_lines(self):
        original = create_journal_entry(
            entry_number="TEST-REV-0001",
            entry_date="2026-10-26",
            description="Original entry",
            lines=self.valid_lines(),
            user=self.user,
        )

        original_lines_before = list(
            original.lines.values_list(
                "account_id", "debit", "credit"
            )
        )

        reversal = reverse_journal_entry(
            entry_id=original.pk,
            user=self.user,
            reversal_number="TEST-REV-0002",
        )

        original.refresh_from_db()

        self.assertEqual(original.status, JournalEntry.Status.REVERSED)
        self.assertEqual(reversal.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            list(original.lines.values_list("account_id", "debit", "credit")),
            original_lines_before,
        )

        reversal_lines = list(
            reversal.lines.values_list("account_id", "debit", "credit")
        )
        self.assertEqual(
            reversal_lines,
            [
                (self.cash.pk, Decimal("0.00"), Decimal("100.00")),
                (self.revenue.pk, Decimal("100.00"), Decimal("0.00")),
            ],
        )

    def test_cannot_reverse_same_entry_twice(self):
        original = create_journal_entry(
            entry_number="TEST-REV-0003",
            entry_date="2026-10-26",
            description="Original entry",
            lines=self.valid_lines(),
            user=self.user,
        )

        reverse_journal_entry(
            entry_id=original.pk,
            user=self.user,
            reversal_number="TEST-REV-0004",
        )

        with self.assertRaises(ValidationError):
            reverse_journal_entry(
                entry_id=original.pk,
                user=self.user,
                reversal_number="TEST-REV-0005",
            )