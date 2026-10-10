import json
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .models import Customer


def telegram_configured():
    return bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', '') and getattr(settings, 'TELEGRAM_CHAT_ID', ''))


def build_reminder_message(customer):
    follow_up_date = (
        customer.follow_up_date.strftime("%d/%m/%Y")
        if customer.follow_up_date
        else "غير مفعّل"
    )

    return (
        '🔔 تذكير بمراجعة عميل\n\n'
        f'الاسم: {customer.name}\n'
        f'الرقم الشخصي: {customer.personal_number}\n'
        f'رقم العربية: {customer.car_number}\n'
        f'المبلغ: {customer.amount} ج\n'
        f'الشغل: {customer.note or "-"}\n\n'
        f'موعد المراجعة: {follow_up_date}\n'
    )


def send_telegram_message(text):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        raise RuntimeError('Telegram غير مُعد: ضع TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في متغيرات البيئة.')

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = urlencode({'chat_id': chat_id, 'text': text}).encode('utf-8')
    request = Request(url, data=payload, method='POST')
    with urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode('utf-8'))
    if not result.get('ok'):
        raise RuntimeError(result.get('description', 'Telegram API error'))
    return result


def send_due_customer_reminders():
    today = timezone.localdate()
    customers = Customer.objects.filter(
        follow_up_enabled=True,
        follow_up_date__lte=today,
        reminder_sent_at__isnull=True,
    )
    sent = 0
    failed = []
    for customer in customers:
        try:
            send_telegram_message(build_reminder_message(customer))
            customer.reminder_sent_at = timezone.now()
            customer.save(update_fields=['reminder_sent_at', 'updated_at'])
            sent += 1
        except Exception as exc:
            failed.append((customer.pk, str(exc)))
    return sent, failed
