# راه‌اندازی واقعی POMP NET روی Railway + نود VPN روی VPS

## معماری لازم

- Railway فقط میزبان پنل مدیریتی PasarGuard و API/صفحه اشتراک است.
- یک VPS با IP عمومی باید PasarGuard Node و Xray-core را اجرا کند. ترافیک کاربران از IP و پورت‌های همین VPS عبور می‌کند، نه از پورت وب Railway.
- Railway Volume باید روی `/var/lib/pasarguard` متصل باشد تا دیتابیس SQLite و گواهی داخلی باقی بمانند.
- Railway HTTPS عمومی را ارائه می‌کند. کانتینر این شاخه با Nginx روی `$PORT` ورودی HTTP Railway را می‌گیرد و به PasarGuard با TLS داخلی روی 127.0.0.1:8000 پروکسی می‌کند.

## تنظیم Railway

در سرویس متصل به همین مخزن:

1. Branch را روی `pompnet-pasarguard-core-v1` قرار بده.
2. Volume بساز و Mount Path را دقیقاً `/var/lib/pasarguard` بگذار.
3. در Networking یک دامنه عمومی بساز و Target Port را روی `8000` تنظیم کن. کد، پورت تزریق‌شده Railway یعنی `PORT` را برای Nginx می‌خواند.
4. Build و Deploy Logs را بررسی کن. باید پیام `PasarGuard is ready` دیده شود و سرویس Railway در وضعیت Active قرار بگیرد.
5. پس از Deploy، در Railway Shell دستور `pasarguard-cli generate-temp-key` را اجرا کن. کلید موقت را فقط در صفحه راه‌اندازی مالک وارد کن. این کلید را در GitHub یا چت قرار نده.

## نصب نود واقعی روی VPS

**این بخش ضروری است؛ بدون Node متصل و Xray فعال، لینک اشتراک به معنی اتصال اینترنتی نیست.**

حداقل منابع رسمی اعلام‌شده برای Node: 1GB RAM، یک هسته CPU و 10GB فضای دیسک؛ پیشنهاد رسمی 2GB RAM، دو هسته و 20GB است.

روی Ubuntu/Debian VPS با دسترسی root:

```bash
curl -fsSL https://raw.githubusercontent.com/PasarGuard/scripts/main/pg-node.sh -o pg-node.sh\nsudo bash pg-node.sh install
```

اسکریپت رسمی وابستگی‌ها و سرویس Node را نصب می‌کند. سپس تنظیمات Node را با دستور زیر باز کن:

```bash
sudo pasarguard-node edit-env
```

در فایل محیطی Node، این مقادیر را با مقادیر خودت تنظیم کن (هیچ مقدار نمونه‌ای را عیناً استفاده نکن):

```dotenv
API_KEY=یک-UUID-قوی-و-خصوصی
NODE_HOST=0.0.0.0
SERVICE_PORT=62050
SERVICE_PROTOCOL=grpc
DEBUG=false
SSL_CERT_FILE=/مسیر/گواهی/معتبر/fullchain.pem
SSL_KEY_FILE=/مسیر/کلید/خصوصی/privkey.pem
XRAY_EXECUTABLE_PATH=/usr/local/bin/xray
XRAY_ASSETS_PATH=/usr/local/share/xray
```

برای گواهی Node از دامنه‌ای که به IP همان VPS اشاره می‌کند و گواهی معتبر عمومی استفاده کن. گواهی self-signed برای اتصال Production با اعتبارسنجی عمومی مناسب نیست. API_KEY را با UUID تصادفی قوی تولید کن و فقط در Secret/تنظیمات خصوصی Node و پنل وارد کن؛ هرگز در مخزن Git قرار نده.

سپس سرویس را با دستورهای مدیریتی نصب‌کننده بررسی و راه‌اندازی مجدد کن:

```bash
sudo pasarguard-node restart
sudo pasarguard-node status
sudo pasarguard-node logs
```

برای نصب چند Node با نام سفارشی، از گزینه `--name` طبق راهنمای رسمی استفاده کن و مسیر داده/پورت هر Node را جدا نگه دار.

## فایروال VPS

- TCP 62050: فقط برای API مدیریتی Node؛ بهتر است دسترسی آن را به IPهای لازم محدود کنی، اگر پنل و Node از شبکه قابل دسترس یکدیگر هستند.
- پورت‌های inbound کاربر (برای نمونه TCP 443) فقط پس از ساخت inbound و Host در پنل باز شوند.
- پورت 8000 پنل Railway یا 2096 را به‌عنوان پورت VPN فرض نکن.
- پورت‌های واقعی باید با inbound و Host تعریف‌شده در PasarGuard یکسان باشند.

## اتصال Node به پنل

در داشبورد PasarGuard:

1. وارد بخش Nodes شو و Add Node را بزن.
2. آدرس Node را دامنه‌ای بگذار که به IP عمومی VPS اشاره می‌کند.
3. پورت را `62050` و پروتکل را `gRPC` انتخاب کن.
4. API Key را دقیقاً همان مقدار خصوصی `API_KEY` نود قرار بده.
5. اتصال را Check کن و تا نمایش وضعیت متصل/سالم ادامه نده.
6. سپس Xray backend/core را برای همان Node فعال و یک Host با دامنه، پورت و TLS/Reality هماهنگ بساز.
7. inboundها را در هسته ایجاد و به Node/Host مربوط اختصاص بده. هر پورت عمومی باید روی VPS باز و در Xray واقعاً در حال listen باشد.

پورت 62050 پورت کنترل Node است؛ پورت کانفیگ کاربران جداست و از تنظیمات inbound/Host می‌آید.

## ساخت و آزمایش کانفیگ

1. در پنل یک کاربر آزمایشی با حجم و تاریخ انقضای محدود بساز.
2. یک inbound پشتیبانی‌شده (VLESS/VMess/Trojan/Shadowsocks) به Node و Host متصل بساز.
3. لینک اشتراک همان کاربر را از خود پنل دریافت کن.
4. لینک را در v2rayNG وارد کن و اتصال را برقرار کن.
5. در پنل باید مصرف ترافیک/آخرین اتصال Node یا لاگ Xray تغییر کند. صرف ساخته‌شدن لینک یا پاسخ HTTP صفحه اشتراک تست اتصال VPN نیست.

## وضعیت مهاجرت داده قدیمی

این شاخه دیتابیس Marzban قدیمی را به PasarGuard تبدیل نمی‌کند. دیتابیس، Volume، UUIDها، کاربران، حجم، انقضا و لینک‌های قبلی را نگه دار. تا وقتی backup مستقل نگرفته‌ای و کاربران آزمایشی را با موفقیت در هسته جدید تست نکرده‌ای، سرویس قبلی را حذف یا DNS آن را جابه‌جا نکن.

## محدودیت‌ها و دقت

- مستندات رسمی Node در حال حاضر آن را در مرحله testing/development معرفی می‌کند؛ قبل از انتقال کاربران واقعی، با یک کاربر آزمایشی و VPS کم‌ریسک تست کن.
- این مخزن پیکربندی Railway و ورودی Nginx را آماده می‌کند؛ نصب Node روی VPS و ثبت Node در پنل، به IP، دامنه، گواهی و دسترسی سرور تو نیاز دارد و از GitHub به‌تنهایی انجام نمی‌شود.
- هنوز هیچ اتصال واقعی v2rayNG یا سرور زنده‌ای از این commit اثبات نشده است.
- PasarGuard Panel تحت AGPL-3.0 و PasarGuard Node تحت GPL-3.0 است؛ مجوزها، اعلان‌ها و تعهدات انتشار کد تغییرات را رعایت کن.
