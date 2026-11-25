# راه‌اندازی تولیدی POMP NET + SideRail روی Railway

این راهنما وضعیت واقعی سورس شاخه `main` را توضیح می‌دهد. هدف معماری فعلی، **دو سرویس جدا در یک Railway Project** است؛ SideRail جایگزین فایل Docker ریشه نیست و نباید روی Volume قدیمی Marzban نصب شود.

> وضعیت در زمان ثبت این راهنما: کد ادغام‌شده در `main` و تست‌های CI موجودند؛ اما حساب Railway به‌دلیل پایان Trial اجازه ساخت Project نمی‌دهد. بنابراین هنوز هیچ سرویس، Volume، دامنه یا Deploy عمومی ساخته نشده است.

## ۱) معماری درست

| سرویس Railway | سورس/تنظیمات | پورت داخل کانتینر | Health check | Volume مستقل |
|---|---|---:|---|---|
| `pompnet-panel` | ریشه مخزن، `Dockerfile` و `railway.json` | 8080 | `/health` | `/var/lib/marzban` |
| `pompnet-siderail` | همان مخزن، فایل تنظیمات `siderail/railway.json` و Dockerfile برابر `siderail/Dockerfile` | 8080 | `/healthz` | `/data` |

هر دو سرویس باید از شاخه `main` مخزن زیر ساخته شوند:

`uxurx7rh7e7xr73uue73e8/POMP-NET-MOHAMMAD-SUPER-JINX`

**مهم:** دو Volume را با هم جابه‌جا یا یکی نکن. Volume سرویس اصلی حاوی دیتابیس Marzban است؛ Volume SideRail حاوی دیتابیس SideRail و فایل‌های Xray است. ساخت Volume خالی روی مسیر داده‌دار قبلی می‌تواند داده‌های داخل آن مسیر را پنهان کند.

## ۲) پیش‌نیاز مسدودکننده فعلی

حساب متصل Railway این خطا را برمی‌گرداند:

`Your trial has expired. Please select a plan to continue using Railway.`

تا انتخاب پلن در داشبورد Railway، ایجاد Project یا Deploy از طریق API ممکن نیست. بعد از انتخاب پلن، همین راهنما را از بخش ۳ ادامه بده. انتخاب پلن ممکن است هزینه داشته باشد؛ قبل از تأیید، قیمت و محدودیت‌ها را خودت بررسی کن.

## ۳) ساخت Project

1. وارد داشبورد Railway شو و یک Project خصوصی با نام `POMP-NET-MOHAMMAD-SUPER-JINX` بساز.
2. Environment پیش‌فرض را `production` نگه دار.
3. هر دو سرویس را در همین Project و همین Environment بساز.
4. Region هر دو سرویس را تا حد امکان یکسان انتخاب کن تا ارتباط خصوصی داخلی برقرار باشد.

## ۴) سرویس اصلی POMP NET

1. از New Service، گزینه GitHub Repository را انتخاب کن.
2. مخزن بالا و Branch برابر `main` را انتخاب کن.
3. Builder باید Dockerfile باشد و مسیر Dockerfile برابر `Dockerfile` ریشه باشد.
4. Config-as-code ریشه، `railway.json` است؛ Health check باید `/health` و پورت مقصد دامنه عمومی `8080` باشد.
5. یک Volume مستقل بساز و به همین سرویس متصل کن:
   - Mount path: `/var/lib/marzban`
6. دامنه HTTPS عمومی برای این سرویس بساز. Target port دامنه را `8080` بگذار؛ پورت داخلی Uvicorn برابر 8000 است و نباید به‌عنوان Target port عمومی انتخاب شود.

### متغیرهای سرویس اصلی

این موارد را در Railway → Service → Variables وارد کن. رمز واقعی را فقط در پنل Railway وارد کن، نه در GitHub یا چت.

| Variable | مقدار |
|---|---|
| `PORT` | `8080` |
| `ADMIN_USERNAME` | نام کاربری مدیر موردنظر |
| `ADMIN_PASSWORD` | رمز قوی و خصوصی حداقل ۱۴ کاراکتر |
| `SIDERAIL_INTERNAL_URL` | آدرس خصوصی سرویس SideRail، پس از ساخت آن |
| `SIDERAIL_OWNER_USERNAME` | نام کاربری مالک SideRail |
| `SIDERAIL_OWNER_PASSWORD` | رمز قوی و جداگانه مالک SideRail |
| `SIDERAIL_PUBLIC_URL` | اختیاری؛ دامنه HTTPS عمومی SideRail، فقط اگر برای دسترسی مستقیم ساخته‌ای |

متغیر `SIDERAIL_INTERNAL_URL` را با hostname خصوصی واقعی که Railway برای سرویس SideRail نشان می‌دهد بساز؛ آن را حدس نزن. قالب معمول آدرس خصوصی `http://<private-hostname>:8080` است.

اگر دیتابیس Marzban موجود و دارای مدیر است، Volume قبلی و رمز فعلی را حفظ کن. برای سرویس موجود، بدون پشتیبان‌گیری و برنامه مهاجرت، Volume را حذف/جایگزین نکن و `RESET_ADMIN_PASSWORD` را فعال نکن.

## ۵) سرویس مستقل SideRail

1. در همان Project گزینه New Service → GitHub Repository را بزن و همان مخزن و Branch `main` را انتخاب کن.
2. Build باید Dockerfile باشد.
3. در تنظیمات Config-as-code، فایل پیکربندی را دقیقاً روی `siderail/railway.json` قرار بده.
4. Dockerfile path باید `siderail/Dockerfile` باشد. Build context باید ریشه مخزن باشد تا دستورهای `COPY siderail/...` فایل‌ها را پیدا کنند.
5. Health check برابر `/healthz` و پورت داخلی برابر `8080` باشد.
6. یک Volume جدید و مستقل به این سرویس وصل کن:
   - Mount path: `/data`
7. برای شروع، دامنه عمومی جداگانه برای SideRail ضروری نیست؛ سرویس اصلی از ارتباط خصوصی استفاده می‌کند. اگر دسترسی مستقیم مالک به UI لازم شد، بعداً دامنه عمومی جداگانه بساز و آن را در `SIDERAIL_PUBLIC_URL` سرویس اصلی قرار بده.

### متغیرهای سرویس SideRail

| Variable | مقدار |
|---|---|
| `PORT` | `8080` |
| `NODE_ENV` | `production` |
| `SIDERAIL_DATA_DIR` | `/data` |
| `CORE_DIR` | `/data/core` |
| `CORE_VERSION` | `v26.9.9` |
| `CORE_API_PORT` | `10085` |
| `CORE_INBOUND_BASE_PORT` | `20000` |
| `JWT_SECRET` | حداقل ۴۸ بایت تصادفی، به‌صورت hex؛ Secret |

برای `JWT_SECRET` از Password/Secret generator امن استفاده کن. آن را در فایل‌های مخزن commit نکن. رمز مالک SideRail را با `SIDERAIL_OWNER_PASSWORD` سرویس اصلی یکی نگذار.

## ۶) ترتیب Deploy

1. اول سرویس SideRail را Deploy کن و منتظر وضعیت `SUCCESS` بمان.
2. بررسی کن Volume روی `/data` mount و قابل نوشتن باشد و endpoint `/healthz` سالم باشد.
3. hostname خصوصی SideRail را از Railway کپی کن.
4. در متغیر `SIDERAIL_INTERNAL_URL` سرویس اصلی ثبت کن.
5. متغیرهای `SIDERAIL_OWNER_USERNAME` و `SIDERAIL_OWNER_PASSWORD` را در سرویس اصلی ثبت کن.
6. سپس سرویس اصلی را Deploy کن و منتظر `SUCCESS` بمان.
7. دامنه عمومی سرویس اصلی باید به Target port `8080` متصل باشد.
8. هر دو سرویس باید در یک Environment فعال باشند؛ ارتباط داخلی باید از سرویس اصلی به SideRail برقرار شود.

## ۷) مهاجرت داده؛ قبل از انتقال کاربران

- هیچ دیتابیس یا Volume قدیمی را پاک نکن.
- قبل از هر import، از دیتابیس و تنظیمات Marzban نسخه پشتیبان خارج از Volume بگیر.
- فایل خروجی کاربران را با ابزارهای موجود در پوشه `migration/` بساز و گزارش خطا/کاربران ناسازگار را بررسی کن.
- نگاشت inboundها را دستی بازبینی کن.
- فقط پروتکل‌ها و transportهای پشتیبانی‌شده در SideRail pinned build را منتقل کن: VLESS، VMess و Trojan روی WS/XHTTP/HTTPUpgrade.
- Reality، gRPC، TCP خام، Shadowsocks، Hysteria2 و TUIC در این مدل انتقال تضمین‌شده نیستند و نباید به‌عنوان مهاجرت‌شده اعلام شوند.
- قبل از cutover، تعداد کاربران، UUID/رمز، token اشتراک، تاریخ انقضا، quota، traffic مصرفی، IP limit و inbound assignment را مقایسه کن.
- تا قبل از تکمیل آزمون و rollback، سرویس قدیمی را نگه دار.

## ۸) آزمون‌های اجباری پس از Deploy

- [ ] Deploy هر دو سرویس `SUCCESS` است.
- [ ] `GET /health` روی دامنه عمومی سرویس اصلی HTTP 200 می‌دهد.
- [ ] `/healthz` سرویس SideRail سالم است.
- [ ] Volume سرویس اصلی روی `/var/lib/marzban` و Volume SideRail روی `/data` mount شده‌اند.
- [ ] ورود مدیر POMP NET با اعتبارنامه امن انجام می‌شود.
- [ ] صفحه SideRail در داشبورد POMP NET وضعیت آنلاین واقعی نشان می‌دهد.
- [ ] ساخت یک کاربر آزمایشی از داشبورد POMP NET در SideRail انجام می‌شود.
- [ ] لینک اشتراک واقعی `/sub/<token>` دریافت می‌شود.
- [ ] لینک در v2rayNG روی گوشی و از یک شبکه بیرونی import می‌شود.
- [ ] handshake و تبادل واقعی upload/download و ping بررسی می‌شوند.
- [ ] کاربر آزمایشی حذف می‌شود.
- [ ] بعد از restart سرویس SideRail، کاربران و دیتابیس باقی می‌مانند.
- [ ] برنامه بازگشت به سرویس قبلی آزمایش و مستند می‌شود.

موفقیت Build یا CI به‌تنهایی تأیید اتصال عمومی VPN نیست. فقط بعد از این آزمون‌ها می‌توان Deploy عمومی و اتصال کلاینت را تأیید کرد.

## ۹) نکات امنیتی

- هیچ رمز، JWT، token، private key یا فایل backup واقعی را commit نکن.
- مخزن را خصوصی نگه دار.
- دسترسی مستقیم عمومی به SideRail را در صورت عدم نیاز فعال نکن.
- برای دو سرویس از Volumeهای جداگانه استفاده کن.
- قبل از تغییر متغیرهای حساس یا import بکاپ، نسخه پشتیبان بگیر.
- لاگ‌ها را برای افشای رمز یا token بررسی کن.
- قابلیت import بکاپ SideRail عملیات جایگزینی داده‌های SideRail است؛ فقط با تأیید مالک و بعد از تهیه بکاپ انجام شود.

## ۱۰) وضعیت اجرایی

| مورد | وضعیت |
|---|---|
| کد SideRail و bridge در `main` | ادغام شده |
| تست‌های CI و تونل VLESS آزمایشگاهی | موفق طبق GitHub Actions |
| Railway Project | ساخته نشده؛ پلن لازم است |
| سرویس اصلی و سرویس SideRail در Railway | ساخته نشده |
| Volumeهای تولیدی | ساخته نشده |
| Secrets و private URL | تنظیم نشده |
| دامنه عمومی | ساخته نشده |
| Deploy عمومی | انجام نشده |
| تست v2rayNG از اینترنت | انجام نشده |
| مهاجرت واقعی کاربران | انجام نشده |

**آخرین commit ادغام‌شده در main:** `c7bed67babdf115967c97fc9dc88fe9a0741c9b5`.

این سند مسیر اجرایی را کامل می‌کند، اما محدودیت پلن Railway را دور نمی‌زند و به‌جای Deploy واقعی، وضعیت موفق جعلی نمایش نمی‌دهد.
