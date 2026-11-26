# راهنمای آپدیت امن POMP NET MOHAMMAD × SUPER JINX

این راهنما برای کسانی است که قبلاً همین مخزن را Deploy کرده‌اند. **آپدیت GitHub به‌تنهایی سرویس‌های از قبل اجراشده را به‌روزرسانی نمی‌کند**؛ هر نصب باید جداگانه از روش استقرار خودش به‌روزرسانی شود.

## هشدار سازگاری قبل از اجرا

در commit فعلی شاخه `main`، فایل ریشه `Dockerfile`، runtime رسمی SideRail را می‌سازد و Caddy مسیر اشتراک را از HTTPS/443 به سرویس داخلی 8080 می‌فرستد. داده‌های SideRail در زیرپوشه `/var/lib/marzban/siderail` قرار می‌گیرند تا با فایل‌های قدیمی Marzban در Volume والد تداخل نکنند.

بنابراین:

- اگر نصب شما از همین Dockerfile ریشه و همین runtime فعلی SideRail استفاده می‌کند، مراحل بخش «آپدیت نصب Compose موجود» را دنبال کنید.
- اگر نصب زنده شما هنوز Marzban / MarzbanUpdate یا Dockerfile دیگری را اجرا می‌کند، **این commit را مستقیماً روی همان سرویس Deploy نکنید**. این کار ممکن است runtime را عوض کند؛ حتی اگر فایل‌های قدیمی داخل Volume باقی بمانند. ابتدا باید مسیر مهاجرت سازگار با همان نصب و backup تأیید شود.
- اگر از Railway استفاده می‌کنید، بررسی کنید Deployment فعلی واقعاً از Dockerfile ریشه همین مخزن استفاده می‌کند و Volume پایدار آن به `/var/lib/marzban` متصل است. Volume را حذف یا جابه‌جا نکنید.
- هیچ‌وقت برای آپدیت عادی `docker compose down -v`، `docker volume prune` یا حذف پوشه داده را اجرا نکنید.

## ۱) بررسی نسخه و مسیر فعلی

روی VPS:

```bash
cd /opt/pompnet-super-jinx
git status --short
git log -1 --oneline
docker compose ps
docker compose config
```

قبل از ادامه، نام سرویس‌ها، مسیر Compose و Volume را با نصب خودت تطبیق بده. اگر پوشه پروژه یا نام Volume متفاوت است، دستورها را کورکورانه اجرا نکن.

## ۲) تهیه پشتیبان از Volume (Compose)

ابتدا نام Volume واقعی را از خروجی این دستور پیدا کن:

```bash
docker volume ls
docker inspect pompnet-super-jinx --format '{{json .Mounts}}'
```

در Compose پیش‌فرض این مخزن، Volume داده `pompnet_data` است. اگر نام واقعی Volume همین است، برای گرفتن نسخه پشتیبان سازگارتر از SQLite، سرویس برنامه را موقتاً متوقف کن:

```bash
cd /opt/pompnet-super-jinx
docker compose stop pompnet
mkdir -p backups
docker run --rm -v pompnet_data:/data:ro -v "$PWD/backups:/backup" alpine:3.20 sh -c 'tar -czf /backup/pompnet-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .'
docker compose start pompnet
```

اگر Volume نام دیگری دارد، فقط پس از شناسایی دقیق، نام آن را در دستور جایگزین کن. فایل `.env` را هم جداگانه و امن نگه‌دار؛ آن را در GitHub یا چت ارسال نکن.

## ۳) آپدیت نصب Compose که از قبل همین runtime را دارد

پس از اطمینان از سازگاری runtime و وجود backup:

```bash
cd /opt/pompnet-super-jinx
git pull --ff-only origin main
docker compose build pompnet
docker compose up -d
docker compose ps
docker compose logs --tail=150 pompnet
docker compose logs --tail=100 caddy
```

این دستورات کانتینرها را از سورس جدید بازسازی می‌کنند و Volumeهای نام‌دار را عمداً حذف نمی‌کنند. در صورت خطا، دستورهای حذف Volume یا نصب مجدد را اجرا نکن؛ لاگ‌ها را بررسی کن و به backup دسترسی داشته باش.

## ۴) بررسی سلامت پس از آپدیت

```bash
docker compose ps
curl -fsS http://127.0.0.1:8080/healthz
```

دستور curl بالا فقط وقتی روی خود VPS قابل استفاده است که پورت 8080 به host publish شده باشد؛ در Compose پیش‌فرض فقط expose داخلی است. در حالت عادی health را از وضعیت `docker compose ps` و لاگ برنامه بررسی کن، سپس از مرورگر دامنه را باز کن.

برای بررسی اشتراک واقعی:
1. از پنل یک کاربر واقعی و فعال انتخاب کن.
2. لینک اشتراک همان کاربر را از خود پنل کپی کن؛ توکن را در GitHub، لاگ عمومی یا پیام عمومی قرار نده.
3. آدرس `https://دامنه-واقعی/sub/توکن-واقعی` را با TLS معتبر باز کن.
4. خروجی‌های Clash و sing-box را در کلاینت واقعی بررسی کن.

HTTPS روی پورت پیش‌فرض 443 است؛ لازم نیست `:443` در URL نوشته شود. وجود route در Caddy به‌تنهایی صدور گواهی TLS، DNS صحیح یا دسترسی شبکه را اثبات نمی‌کند.

## ۵) کاربران Railway

برای هر سرویس Railway:
- از همان Project و Service موجود استفاده کن؛ Project جدید نساز مگر اینکه عمداً محیط staging بخواهی.
- قبل از Deploy، از داده‌ها/Volume موجود نسخه پشتیبان بگیر و مطمئن شو Volume به مسیر `/var/lib/marzban` متصل است.
- Variables و Secrets موجود را حفظ کن؛ `.env` یا مقادیر محرمانه را با فایل نمونه جایگزین نکن.
- Deploy را فقط وقتی انجام بده که runtime فعلی همان SideRail ریشه باشد. اگر سرویس هنوز Marzban را اجرا می‌کند، این راهنما مجوز cutover نیست.
- بعد از Deploy، لاگ build، healthcheck و endpoint اشتراک را با توکن واقعی بررسی کن.

## وضعیت تأیید

این سند دستورالعمل نگهداری است، نه ادعای اینکه همه نصب‌های عمومی به‌صورت خودکار آپدیت شده‌اند. Push به GitHub فقط شاخه مخزن را تغییر می‌دهد؛ Railway/VPS هر مالک باید جداگانه Deploy شود. Build موفق هم جایگزین تست دامنه، TLS، اشتراک با توکن واقعی و اتصال کلاینت نیست.
