from django.core.management.base import BaseCommand
from customers.services import send_due_customer_reminders


class Command(BaseCommand):
    help = 'إرسال تذكيرات العملاء المستحقة عبر Telegram.'

    def handle(self, *args, **options):
        sent, failed = send_due_customer_reminders()
        self.stdout.write(self.style.SUCCESS(f'تم إرسال {sent} تذكير.'))
        for customer_id, error in failed:
            self.stderr.write(self.style.ERROR(f'العميل #{customer_id}: {error}'))
