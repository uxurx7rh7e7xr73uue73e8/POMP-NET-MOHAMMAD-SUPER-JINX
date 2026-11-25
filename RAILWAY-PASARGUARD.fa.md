# راه‌اندازی POMP NET روی Railway + نود VPN روی VPS

## معماری
- Railway فقط میزبان پنل مدیریتی PasarGuard و API/صفحه اشتراک است.
- ترافیک VPN از VPS عمومی دارای PasarGuard Node و Xray-core عبور می‌کند، نه از پورت وب Railway.
- Volume باید دقیقاً روی `/var/lib/pasarguard` متصل باشد.
- Nginx داخل کانتینر روی TCP پورت ثابت `8000` گوش می‌دهد و درخواست‌ها را با TLS داخلی به PasarGuard روی `8001` می‌فرستد.

## تنظیم Railway
1. منبع سرویس را به مخزن `uxurx7rh7e7xr73uue73e8/POMP-NET-MOHAMMAD-SUPER-JINX` و شاخه `pompnet-pasarguard-core-v1` متصل کن.
2. یک Volume با Mount Path دقیق `/var/lib/pasarguard` به همین سرویس متصل کن. بدون Volume برنامه عمداً متوقف می‌شود تا دیتابیس موقت ساخته نشود.
3. در Settings → Networking دامنه بساز و Target Port را دقیقاً `8000` قرار بده.
4. Build/Deploy Logs را بررسی کن. پیام `PasarGuard is ready` باید دیده شود.
5. پس از موفقیت Deploy، از محیط امن سرور دستور `pasarguard-cli generate-temp-key` را اجرا کن و کلید موقت را فقط در صفحه راه‌اندازی مالک وارد کن. کلید را در GitHub یا چت منتشر نکن.

## نصب Node روی VPS
این مرحله برای ساخت کانفیگ متصل به اینترنت ضروری است. روی Ubuntu/Debian با دسترسی root:

```bash
curl -fsSL https://raw.githubusercontent.com/PasarGuard/scripts/main/pg-node.sh -o pg-node.sh
sudo bash pg-node.sh install
```

برای جزئیات و گزینه‌های نصب، راهنمای رسمی را ببین: https://docs.pasarguard.org/en/node/

پس از نصب، وضعیت Node را بررسی کن:
```bash
sudo pg-node status
sudo pg-node logs
```

پورت کنترل پیش‌فرض Node برابر `62050` و پروتکل پیش‌فرض `gRPC` است. برای TLS، دامنه‌ای لازم است که به IP عمومی همان VPS اشاره کند. API Key باید UUID معتبر و محرمانه باشد؛ آن را در GitHub یا چت قرار نده.

## اتصال Node و ساخت VLESS
1. در پنل، بخش Nodes را باز کن و Node جدید اضافه کن.
2. آدرس را روی دامنه VPS، پورت را روی `62050` و پروتکل را روی `gRPC` قرار بده؛ API Key را دقیقاً با مقدار محرمانه Node یکسان وارد کن.
3. تا وقتی وضعیت Node سالم/متصل نشده، کانفیگ نساز.
4. برای Node یک Host و inbound از نوع VLESS TCP بساز. پورت کاربر را `443` بگذار و TLS/Reality و دامنه را دقیقاً مطابق تنظیم Xray و گواهی انتخاب کن.
5. پورت TCP 443 را در فایروال VPS باز کن و روی همان VPS بررسی کن Xray واقعاً روی 443 در حال listen است.
6. یک کاربر آزمایشی بساز، لینک اشتراک را از خود پنل بگیر و در v2rayNG تست کن. افزایش مصرف/اتصال در پنل یا لاگ Xray باید دیده شود.

## نکات مهم
- پورت `8000` فقط پورت وب پنل Railway است؛ پورت `443` کانفیگ باید روی VPS و Xray باشد.
- Railway TCP Proxy پورت عمومی اختصاصی خودش را می‌دهد و تضمین نمی‌کند پورت عمومی دقیقاً 443 باشد؛ برای 443 ثابت از VPS استفاده کن.
- این شاخه دیتابیس Marzban قدیمی را به PasarGuard تبدیل نمی‌کند. قبل از مهاجرت، از دیتابیس و Volume قبلی backup مستقل بگیر و سرویس قبلی را حذف نکن.
- هنوز Deploy یا تست واقعی v2rayNG انجام نشده است. صرف ساخته‌شدن لینک اشتراک، اثبات اتصال نیست.
- قابلیت Node در اکوسیستم PasarGuard همچنان باید ابتدا با کاربر آزمایشی ارزیابی شود.
