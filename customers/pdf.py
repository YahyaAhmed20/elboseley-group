from io import BytesIO
from pathlib import Path

from django.http import FileResponse


def _shape(text):
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text or ''))
    except ImportError:
        return text or ''


def customer_pdf_response(customer):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    base = Path(__file__).resolve().parent / 'fonts'
    regular = str(base / 'DejaVuSans.ttf')
    bold = str(base / 'DejaVuSans-Bold.ttf')
    if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('DejaVuSans', regular))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    right = width - 45
    y = height - 55

    pdf.setFont('DejaVuSans-Bold', 18)
    pdf.drawRightString(right, y, _shape('بيانات العميل'))
    y -= 42
    pdf.setFont('DejaVuSans', 11)

    rows = [
        ('اسم العميل', customer.name),
        ('الرقم الشخصي', customer.personal_number),
        ('رقم العربية', customer.car_number),
        ('المبلغ', f'{customer.amount} ج'),
        ('موعد المراجعة', customer.follow_up_date.strftime('%d/%m/%Y') if customer.follow_up_date else 'غير مفعّل'),
        ('تاريخ التسجيل', customer.created_at.strftime('%d/%m/%Y')),
    ]
    for label, value in rows:
        pdf.setFont('DejaVuSans-Bold', 11)
        pdf.drawRightString(right, y, _shape(f'{label}:'))
        pdf.setFont('DejaVuSans', 11)
        pdf.drawRightString(right - 145, y, _shape(str(value)))
        y -= 28

    y -= 8
    pdf.setFont('DejaVuSans-Bold', 12)
    pdf.drawRightString(right, y, _shape('الشغل / الملاحظة'))
    y -= 25
    pdf.setFont('DejaVuSans', 10)
    note = customer.note or '-'
    words = note.split()
    line = ''
    for word in words:
        candidate = f'{line} {word}'.strip()
        if pdf.stringWidth(_shape(candidate), 'DejaVuSans', 10) > 470:
            pdf.drawRightString(right, y, _shape(line))
            y -= 20
            line = word
        else:
            line = candidate
    if line:
        pdf.drawRightString(right, y, _shape(line))

    pdf.setFont('DejaVuSans', 8)
    pdf.drawRightString(right, 30, _shape('Rovana Inventory System'))
    pdf.save()
    buffer.seek(0)
    filename = f'customer_{customer.pk}.pdf'
    return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')
