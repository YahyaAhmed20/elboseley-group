from django.test import TestCase

# Create your tests here.

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Item
from inventory.models import StockIssue, StockMovement
from inventory.services import (
    create_stock_issue,
    update_stock_issue,
    delete_stock_issue,
)


class StockIssueServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="inventory_test_user",
            password="test-password",
            role="keeper",
        )
        self.item = Item.objects.create(
            name="Test stock item",
            opening_balance=Decimal("10.00"),
        )

    def create_issue(self, qty="3.00", number="TEST-ISSUE-001"):
        return create_stock_issue(
            invoice_number=number,
            recipient="Test recipient",
            issue_type=StockIssue.IssueType.INTERNAL,
            notes="",
            lines=[{
                "item_id": self.item.pk,
                "qty": Decimal(qty),
                "unit_price": Decimal("2.00"),
            }],
            user=self.user,
        )

    def test_create_issue_reduces_stock(self):
        issue = self.create_issue()
        self.item.refresh_from_db()

        self.assertEqual(self.item.current_qty, Decimal("7.00"))
        self.assertEqual(issue.lines.count(), 1)

    def test_update_issue_replaces_stock_quantity(self):
        issue = self.create_issue(qty="3.00")
        update_stock_issue(
            issue_id=issue.pk,
            invoice_number=issue.invoice_number,
            recipient="Updated recipient",
            issue_type=StockIssue.IssueType.INTERNAL,
            notes="Updated",
            lines=[{
                "item_id": self.item.pk,
                "qty": Decimal("4.00"),
                "unit_price": Decimal("2.00"),
            }],
        )

        self.item.refresh_from_db()
        issue.refresh_from_db()

        self.assertEqual(self.item.current_qty, Decimal("6.00"))
        self.assertEqual(issue.recipient, "Updated recipient")
        self.assertEqual(issue.lines.count(), 1)

    def test_update_issue_rejects_insufficient_stock_without_changes(self):
        issue = self.create_issue(qty="3.00")

        with self.assertRaises(ValidationError):
            update_stock_issue(
                issue_id=issue.pk,
                invoice_number=issue.invoice_number,
                recipient=issue.recipient,
                issue_type=issue.issue_type,
                notes=issue.notes,
                lines=[{
                    "item_id": self.item.pk,
                    "qty": Decimal("11.00"),
                    "unit_price": Decimal("2.00"),
                }],
            )

        self.item.refresh_from_db()
        issue.refresh_from_db()

        self.assertEqual(self.item.current_qty, Decimal("7.00"))
        self.assertEqual(issue.lines.first().qty, Decimal("3.00"))

    def test_delete_issue_restores_stock(self):
        issue = self.create_issue(qty="3.00")
        delete_stock_issue(issue_id=issue.pk)

        self.item.refresh_from_db()

        self.assertEqual(self.item.current_qty, Decimal("10.00"))
        self.assertFalse(StockIssue.objects.filter(pk=issue.pk).exists())
        self.assertFalse(
            StockMovement.objects.filter(issue_line__issue_id=issue.pk).exists()
        )
