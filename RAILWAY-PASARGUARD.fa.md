# راه‌اندازی POMP NET با هسته رسمی PasarGuard روی Railway

این شاخه برای ساخت پنل PasarGuard روی Railway آماده شده است. Dockerfile ریشه دیگر Marzban را اجرا نمی‌کند؛ image رسمی `pasarguard/panel` را می‌گیرد و اسکریپت `start-railway.sh` پورت پویا و اجرای migration رسمی را تنظیم می‌کند.

## تنظیمات ضروری Railway

پس از انتخاب شاخه `pompnet-pasarguard-core-v1` برای سرویس:

1. در Settings → Networking، دامنه عمومی بساز و Target Port را روی `8000` قرار بده.
2. در Volumes یک Volume بساز و دقیقاً روی `/var/lib/pasarguard` mount کن. بدون این Volume دیتابیس SQLite و اطلاعات پنل پس از تعویض کانتینر ماندگار نیستند.
3. هیچ `network_mode: host` یا پورت TLS سفارشی لازم نیست. HTTPS عمومی را Railway ارائه می‌کند؛ داخل کانتینر PasarGuard روی HTTP پورت `$PORT` گوش می‌دهد.
4. پس از Deploy موفق، از Railway Shell دستور زیر را اجرا کن تا کلید یک‌بارمصرف ساخت مالک تولید شود:
   ```bash
   pasarguard cli generate-temp-key
   ```
   کلید را فقط در داشبورد خودت استفاده کن و در Git یا چت منتشر نکن.

## نکته حیاتی درباره اتصال کانفیگ‌ها

این سرویس، پنل مدیریتی PasarGuard است؛ صرف Deploy شدن پنل به معنی وجود سرور VPN عمومی نیست. برای اتصال واقعی VLESS/VMess/Trojan و ساخت لینک اشتراک قابل استفاده در v2rayNG باید یک PasarGuard Node روی VPS دارای IP عمومی نصب و از بخش Nodes به این پنل متصل شود. ترافیک VPN را نباید به دامنه HTTP پنل Railway یا پورت وب 8000 فرستاد.

Railway برای پنل و API مدیریتی استفاده می‌شود. Node روی VPS، پورت‌های واقعی inbound، TLS/Reality و دامنه/مسیر اشتراک را مدیریت می‌کند. این مخزن هنوز انتقال کاربران، حجم/انقضا، UUIDها و inboundهای دیتابیس Marzban قدیمی را انجام نداده است؛ دیتابیس قبلی را حذف نکن.

## محدودیت‌های فعلی

- این تغییر فقط Docker build/startup پنل PasarGuard را برای Railway آماده می‌کند.
- اتصال Node واقعی، تنظیم inboundها، دامنه اشتراک و آزمون بیرونی v2rayNG هنوز انجام نشده است.
- هیچ رمز یا توکنی در Git قرار نده.
- image فعلاً از برچسب `latest` استفاده می‌کند؛ برای استقرار پایدار باید پس از تعیین نسخه آزمایش‌شده به نسخه ثابت pin شود.
- PasarGuard تحت AGPL-3.0 است؛ اعلان مجوز و تعهدات ارائه کد منبع نسخه تغییریافته را رعایت کن.
