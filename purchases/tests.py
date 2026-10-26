from django.test import TestCase
from django.test import Client
from django.urls import reverse
# Create your tests here.
from django.core.exceptions import PermissionDenied
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import Account, JournalEntry
from finance.services import ensure_default_accounts, create_journal_entry
from catalog.models import Item
from finance.models import CashboxTransaction
from finance.services import get_cashbox_balance
from purchases.models import PurchaseInvoice, SupplierAccountEntry
from purchases.services import pay_purchase_invoice
from supplier.models import Supplier

class PurchaseAccountingFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="purchase_accounting_test",
            password="test-password",
            role="admin",
        )
        self.accounts = ensure_default_accounts()

    def test_partial_purchase_journal_is_balanced(self):
        entry = create_journal_entry(
            entry_number="TEST-PUR-001",
            entry_date="2026-10-26",
            description="اختبار شراء جزئي",
            reference_type="purchase_invoice",
            reference_id=1,
            user=self.user,
            lines=[
                {
                    "account_id": self.accounts["1200"].pk,
                    "debit": Decimal("10000.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": self.accounts["1000"].pk,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("4000.00"),
                },
                {
                    "account_id": self.accounts["2000"].pk,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("6000.00"),
                },
            ],
        )

        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            sum(line.debit for line in entry.lines.all()),
            Decimal("10000.00"),
        )
        self.assertEqual(
            sum(line.credit for line in entry.lines.all()),
            Decimal("10000.00"),
        )

    def test_rejects_unbalanced_purchase_journal(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                entry_number="TEST-PUR-002",
                entry_date="2026-10-26",
                description="اختبار قيد غير متوازن",
                user=self.user,
                lines=[
                    {
                        "account_id": self.accounts["1200"].pk,
                        "debit": Decimal("10000.00"),
                        "credit": Decimal("0.00"),
                    },
                    {
                        "account_id": self.accounts["2000"].pk,
                        "debit": Decimal("0.00"),
                        "credit": Decimal("9000.00"),
                    },
                ],
            )

        self.assertFalse(
            JournalEntry.objects.filter(
                entry_number="TEST-PUR-002"
            ).exists()
        )





    def test_supplier_payment_journal_is_balanced(self):
        entry = create_journal_entry(
            entry_number="TEST-PAY-001",
            entry_date="2026-10-26",
            description="اختبار سداد مورد",
            user=self.user,
            lines=[
                {
                    "account_id": self.accounts["2000"].pk,
                    "debit": Decimal("2000.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": self.accounts["1000"].pk,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("2000.00"),
                },
            ],
        )

        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            sum(line.debit for line in entry.lines.all()),
            Decimal("2000.00"),
        )
        self.assertEqual(
            sum(line.credit for line in entry.lines.all()),
            Decimal("2000.00"),
        )
        
        
        

class SupplierPaymentServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="supplier_payment_test",
            password="test-password",
            role="admin",
        )
        self.supplier = Supplier.objects.create(
            name="Supplier Payment Test",
        )
        self.invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number="PAY-TEST-001",
            payment_type=PurchaseInvoice.PaymentType.CREDIT,
            total=Decimal("100.00"),
            paid_amount=Decimal("0.00"),
            created_by=self.user,
        )
        self.accounts = ensure_default_accounts()

    def add_cash(self, amount):
        CashboxTransaction.objects.create(
            kind=CashboxTransaction.Kind.OPENING,
            amount=Decimal(amount),
            description="Test opening cash",
            created_by=self.user,
        )

    def test_partial_payment_updates_invoice_and_supplier_account(self):
        self.add_cash("200.00")

        pay_purchase_invoice(
            invoice_id=self.invoice.pk,
            amount=Decimal("40.00"),
            user=self.user,
            notes="Test partial payment",
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("40.00"))
        self.assertEqual(self.invoice.remaining_amount, Decimal("60.00"))
        self.assertEqual(
            SupplierAccountEntry.objects.filter(
                invoice=self.invoice,
                entry_type=SupplierAccountEntry.EntryType.PAYMENT,
                debit=Decimal("40.00"),
            ).count(),
            1,
        )
        self.assertEqual(get_cashbox_balance(), Decimal("160.00"))

        payment_entry = JournalEntry.objects.get(
            reference_type="purchase_payment",
        )
        self.assertEqual(
            payment_entry.status,
            JournalEntry.Status.POSTED,
        )
        self.assertEqual(
            sum(line.debit for line in payment_entry.lines.all()),
            Decimal("40.00"),
        )
        self.assertEqual(
            sum(line.credit for line in payment_entry.lines.all()),
            Decimal("40.00"),
        )


    
    def test_full_payment_settles_invoice_and_balances_accounts(self):
        self.add_cash("200.00")

        pay_purchase_invoice(
            invoice_id=self.invoice.pk,
            amount=Decimal("100.00"),
            user=self.user,
            notes="Test full payment",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(self.invoice.paid_amount, Decimal("100.00"))
        self.assertEqual(self.invoice.remaining_amount, Decimal("0.00"))
        self.assertEqual(
            self.invoice.payment_type,
            PurchaseInvoice.PaymentType.CASH,
        )
        self.assertEqual(get_cashbox_balance(), Decimal("100.00"))

        payment = SupplierAccountEntry.objects.get(
            invoice=self.invoice,
            entry_type=SupplierAccountEntry.EntryType.PAYMENT,
        )
        self.assertEqual(payment.debit, Decimal("100.00"))

        journal = JournalEntry.objects.get(
            reference_type="purchase_payment",
        )
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            sum(line.debit for line in journal.lines.all()),
            Decimal("100.00"),
        )
        self.assertEqual(
            sum(line.credit for line in journal.lines.all()),
            Decimal("100.00"),
        )

    def test_rejects_payment_after_invoice_is_fully_paid(self):
        self.add_cash("200.00")

        pay_purchase_invoice(
            invoice_id=self.invoice.pk,
            amount=Decimal("100.00"),
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            pay_purchase_invoice(
                invoice_id=self.invoice.pk,
                amount=Decimal("1.00"),
                user=self.user,
            )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("100.00"))
        self.assertEqual(get_cashbox_balance(), Decimal("100.00"))

        self.assertEqual(
            CashboxTransaction.objects.filter(
                purchase_invoice=self.invoice,
                kind=CashboxTransaction.Kind.EXPENSE,
            ).count(),
            1,
        )
        self.assertEqual(
            SupplierAccountEntry.objects.filter(
                invoice=self.invoice,
                entry_type=SupplierAccountEntry.EntryType.PAYMENT,
            ).count(),
            1,
        )
        self.assertEqual(
            JournalEntry.objects.filter(
                reference_type="purchase_payment",
            ).count(),
            1,
        )

    def test_supplier_statement_reflects_partial_payment(self):
        self.add_cash("200.00")

        SupplierAccountEntry.objects.create(
            supplier=self.supplier,
            invoice=self.invoice,
            entry_type=SupplierAccountEntry.EntryType.PURCHASE,
            debit=Decimal("0.00"),
            credit=Decimal("100.00"),
            notes="Test purchase entry",
            created_by=self.user,
        )

        pay_purchase_invoice(
            invoice_id=self.invoice.pk,
            amount=Decimal("40.00"),
            user=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "supplier:supplier_statement",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_purchases"], Decimal("100.00"))
        self.assertEqual(response.context["total_paid"], Decimal("40.00"))
        self.assertEqual(response.context["current_balance"], Decimal("60.00"))
        self.assertEqual(len(response.context["rows"]), 2)


        
        
    def test_rejects_payment_above_remaining_without_changes(self):
        self.add_cash("200.00")

        with self.assertRaises(ValidationError):
            pay_purchase_invoice(
                invoice_id=self.invoice.pk,
                amount=Decimal("101.00"),
                user=self.user,
            )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("0.00"))
        self.assertFalse(
            CashboxTransaction.objects.filter(
                purchase_invoice=self.invoice,
                kind=CashboxTransaction.Kind.EXPENSE,
            ).exists()
        )
        self.assertFalse(
            SupplierAccountEntry.objects.filter(
                invoice=self.invoice,
                entry_type=SupplierAccountEntry.EntryType.PAYMENT,
            ).exists()
        )

    def test_rejects_payment_when_cashbox_is_insufficient(self):
        self.add_cash("10.00")

        with self.assertRaises(ValidationError):
            pay_purchase_invoice(
                invoice_id=self.invoice.pk,
                amount=Decimal("20.00"),
                user=self.user,
            )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("0.00"))
        self.assertFalse(
            CashboxTransaction.objects.filter(
                purchase_invoice=self.invoice,
                kind=CashboxTransaction.Kind.EXPENSE,
            ).exists()
        )
        self.assertFalse(
            SupplierAccountEntry.objects.filter(
                invoice=self.invoice,
                entry_type=SupplierAccountEntry.EntryType.PAYMENT,
            ).exists()
        )
        
        
        

class SupplierPaymentPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.keeper = User.objects.create_user(
            username="payment_keeper_test",
            password="test-password",
            role="keeper",
        )
        self.viewer = User.objects.create_user(
            username="payment_viewer_test",
            password="test-password",
            role="viewer",
        )
        self.admin = User.objects.create_user(
            username="payment_admin_test",
            password="test-password",
            role="admin",
        )

        self.supplier = Supplier.objects.create(
            name="Payment Permission Supplier",
        )
        self.invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number="PAY-PERM-001",
            payment_type=PurchaseInvoice.PaymentType.CREDIT,
            total=Decimal("100.00"),
            paid_amount=Decimal("0.00"),
            created_by=self.admin,
        )

        self.client = Client()
        self.url = reverse(
            "purchases:invoice_pay",
            kwargs={"pk": self.invoice.pk},
        )

    def test_admin_can_open_payment_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_keeper_cannot_open_payment_page(self):
        self.client.force_login(self.keeper)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

        

    def test_viewer_cannot_open_payment_page(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)