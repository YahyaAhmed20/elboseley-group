عشان اعمل اي app 
mkdir apps\finance
python manage.py startapp finance apps/finance


ده لو ف اي تعديل ف البرنامج 
pyinstaller run.py --add-data "templates;templates" --add-data "static;static"
pyinstaller run.py --add-data "templates;templates" --add-data "static;static" --hidden-import=waitress --hidden-import=django --hidden-import=rest_framework

الفرق بين الويب والبرنامج ان ف الويب بتعمل hide ل white storage from middleware and under page + databse 



C:\Users\hp\AppData\Local\Rovana\db.sqlite3


🔥 الخطوة اللي بعدها (لو عايز تبقى تقيل بجد)

نظبط:

✔ Setup Installer (زي البرامج)
✔ Icon رسمي
✔ Splash screen
✔ Auto backup
✔ حماية البرنامج


انا اعدل البرمانج وبعدين اشغل build.py 

ابعت:
run/
├── run.exe
├── update.bat
├── version.txt


1. يفتح مجلد run/ في Downloads
2. يضغط update.bat
   → خلص
الـ update.bat بيعمل الباقي أوتوماتيك.



{% load static %}
<!doctype html>
<html lang="ar" dir="rtl">

<head>
    <meta charset="utf-8">
    <title>إيصال استلام جهاز #{{ order.device.code }}</title>

    <script src="{% static 'qz/qz-tray.js' %}"></script>
    <script src="{% static 'qz/qz-print.js' %}"></script>

    <style>
        body {
            font-family: Arial, sans-serif;
            width: 80mm;
            margin: auto;
            padding: 8mm;
            font-size: 13px;
        }

        .center {
            text-align: center;
        }

        .line {
            border-top: 1px dashed #000;
            margin: 8px 0;
        }

        .row {
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
            gap: 10px;
        }

        .actions {
            margin-top: 20px;
            text-align: center;
        }

        button {
            padding: 10px 20px;
            cursor: pointer;
            font-size: 14px;
        }

        @media print {
            .actions {
                display: none;
            }

            @page {
                size: 80mm auto;
                margin: 0;
            }

            body {
                width: 72mm;
                padding: 4mm;
            }
        }
    </style>
</head>

<body>

    <div class="center">
        <h3>إيصال استلام جهاز #{{ order.device.code }}</h3>
        <div>البوصيلي جروب</div>
    </div>

    <div class="line"></div>

    <div class="row">
        <b>العميل</b>
        <span>{{ order.device.customer.name }}</span>
    </div>

    <div class="row">
        <b>الهاتف</b>
        <span>{{ order.device.customer.phone }}</span>
    </div>

    <div class="row">
        <b>كود الجهاز</b>
        <span>#{{ order.device.code }}</span>
    </div>

    <div class="row">
        <b>الجهاز</b>
        <span>{{ order.device.device_type }}</span>
    </div>

    <div class="row">
        <b>العطل</b>
        <span>{{ order.fault_description }}</span>
    </div>

    <div class="row">
        <b>العربون</b>
        <span>{{ order.deposit }} ج.م</span>
    </div>

    <div class="row">
        <b>التاريخ</b>
        <span>{{ order.received_at|date:'d/m/Y H:i' }}</span>
    </div>

    <div class="line"></div>

    <div class="center">
        احتفظ بهذا الإيصال عند الاستلام
    </div>

    <div class="actions">
        <button onclick="printReceipt()">🖨️ طباعة الإيصال</button>
    </div>

   <script>
const printerName = "Argox OS-2130D PPLA";

async function printReceipt() {
    try {
        if (!qz.websocket.isActive()) {
            await qz.websocket.connect();
        }

        // =====================================================
        // 60 × 40 mm @ 203 DPI
        // =====================================================

        const width = 480;
        const height = 320;

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");

        // Background
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);

        ctx.fillStyle = "#000000";
        ctx.direction = "rtl";
        ctx.textBaseline = "top";

        // =====================================================
        // العنوان
        // =====================================================

        ctx.textAlign = "center";
        ctx.font = "bold 29px Arial";

        ctx.fillText(
            "إيصال استلام جهاز #{{ order.device.code }}",
            width / 2,
            6
        );

        ctx.font = "bold 20px Arial";

        ctx.fillText(
            "البوصيلي جروب",
            width / 2,
            34
        );

        // =====================================================
        // الخط الفاصل
        // =====================================================

        ctx.beginPath();
        ctx.moveTo(12, 60);
        ctx.lineTo(width - 12, 60);
        ctx.stroke();

        // =====================================================
        // بيانات العميل - اليمين
        // =====================================================

        ctx.font = "bold 18px Arial";
        ctx.textAlign = "right";

        let rightY = 70;

        function rightText(value) {
            ctx.fillText(value, width - 14, rightY);
            rightY += 29;
        }

        rightText(
            "العميل: {{ order.device.customer.name|escapejs }}"
        );

        rightText(
            "الهاتف: {{ order.device.customer.phone|escapejs }}"
        );

        rightText(
            "كود الجهاز: #{{ order.device.code }}"
        );

        rightText(
            "الجهاز: {{ order.device.device_type|escapejs }}"
        );

        // =====================================================
        // العطل - الشمال
        // =====================================================

        const fault =
            "{{ order.fault_description|escapejs }}";

        ctx.font = "bold 18px Arial";
        ctx.textAlign = "left";

        const faultX = 115;
        const faultWidth = 125;

        function wrapText(text, maxWidth) {
            const words = text.split(/\s+/);
            const lines = [];
            let line = "";

            for (const word of words) {
                const testLine = line
                    ? line + " " + word
                    : word;

                if (ctx.measureText(testLine).width > maxWidth) {
                    if (line) {
                        lines.push(line);
                    }

                    line = word;
                } else {
                    line = testLine;
                }
            }

            if (line) {
                lines.push(line);
            }

            return lines;
        }

        let faultY = 70;

        ctx.fillText(
            "العطل:",
            faultX,
            faultY
        );

        faultY += 25;

        const faultLines = wrapText(
            fault,
            faultWidth
        );

        faultLines.slice(0, 3).forEach(function(line) {
            ctx.fillText(
                line,
                faultX,
                faultY
            );

            faultY += 23;
        });

        // =====================================================
        // العربون
        // =====================================================

        ctx.font = "bold 18px Arial";

        ctx.fillText(
            "العربون: {{ order.deposit }} ج.م",
            faultX,
            172
        );

        // =====================================================
        // التاريخ
        // =====================================================

        ctx.font = "bold 18px Arial";

        ctx.fillText(
            "{{ order.received_at|date:'d/m/Y H:i' }}",
            faultX,
            198
        );

        // =====================================================
        // الخط السفلي
        // =====================================================

        ctx.beginPath();
        ctx.moveTo(12, 270);
        ctx.lineTo(width - 12, 270);
        ctx.stroke();

        // =====================================================
        // الرسالة الأخيرة
        // =====================================================

        ctx.textAlign = "center";
        ctx.font = "bold 15px Arial";

        ctx.fillText(
            "احتفظ بهذا الإيصال عند استلام",
            width / 2,
            282
        );

        // =====================================================
        // Base64
        // =====================================================

        const base64 = canvas
            .toDataURL("image/png")
            .split(",")[1];

        // =====================================================
        // QZ CONFIG
        // =====================================================

        const config = qz.configs.create(
            printerName,
            {
                units: "in",

                margins: {
                    top: 0,
                    right: 0,
                    bottom: 0,
                    left: 0
                },

                scaleContent: false,

                interpolation: "nearest-neighbor",

                orientation: "portrait"
            }
        );

        const data = [{
            type: "pixel",
            format: "image",
            flavor: "base64",
            data: base64
        }];

        await qz.print(config, data);

        alert("تم طباعة الإيصال بنجاح.");

        window.location.href =
            "{% url 'servicecenter:repair_receive' %}";

    } catch (error) {
        console.error(error);

        alert(
            "حدث خطأ أثناء الطباعة:\n" + error
        );
    }
}
</script>

</body>

</html>


التعديل المقترح
نرفع الخط درجة بسيطة:
ctx.font = "bold 29px Arial";

للعنوان بدل 27px.
ctx.font = "bold 20px Arial";

لـ البوصيلي جروب بدل 19px.
ونخلي بيانات اليمين:
ctx.font = "bold 18px Arial";

بدل 17px.
ونفس الشيء للعطل والعربون والتاريخ:
ctx.font = "bold 18px Arial";

تحريك المحتوى الشمال
عندك الآن:
const faultX = 95;
const faultWidth = 145;

خليها:
const faultX = 115;
const faultWidth = 125;

يعني +20px ناحية اليمين.
لكن خُد بالك من نقطة مهمة
أنت سألت: لو عايز أكبر الخط أغير إيه؟
أي سطر فيه:
ctx.font = "bold 17px Arial";

الرقم 17 هو حجم الخط.
مثلاً:
17px → 18px → 19px → 20px

كلما زوّدت الرقم، الخط يكبر.
أما المحتوى الشمال، فالمتحكم في مكانه هو:
const faultX = 95;

مثلاً:
95  → المكان الحالي
105 → يمين 10px
115 → يمين 20px
125 → يمين 30px

لكن كلما زوّدت faultX، لازم غالبًا تقلل faultWidth لأنك بتقرب المحتوى من بيانات اليمين.
مثال:
const faultX = 115;
const faultWidth = 125;

إذن غيّر هذه الأرقام فقط الآن:
ctx.font = "bold 29px Arial";

ctx.font = "bold 20px Arial";

ctx.font = "bold 18px Arial";

const faultX = 115;
const faultWidth = 125;

ولا تغيّر أي شيء في QZ أو مقاس الـ Canvas أو إعدادات الطابعة.