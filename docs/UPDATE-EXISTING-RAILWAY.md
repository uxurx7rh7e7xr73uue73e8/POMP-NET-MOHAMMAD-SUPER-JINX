# به‌روزرسانی همان پروژهٔ موجود در Railway

این راهنما برای **آپدیت سرویس قبلی** است؛ پروژه یا سرویس تازه نسازید و سرویس قبلی را حذف نکنید.

## سورس این شاخه

- Repository: `uxurx7rh7e7xr73uue73e8/POMP-NET-MOHAMMAD-SUPER-JINX`
- Branch: `pompnet-pasarguard-core-migration`
- Core فعلی: Marzban + Xray
- Dockerfile: ریشهٔ مخزن
- فایل تنظیمات Railway: `railway.json`

## مراحل آپدیت بدون حذف پروژه

1. وارد همان Project قبلی در Railway شوید.
2. سرویس فعلی پنل را باز کنید؛ روی New Project یا Delete Service نزنید.
3. در Settings → Source، همین Repository را متصل کنید و Branch را روی `pompnet-pasarguard-core-migration` قرار دهید.
4. اگر همین Repository و Branch از قبل متصل است، Source را تغییر ندهید؛ فقط آخرین Commit را Deploy کنید.
5. در Settings → Build مطمئن شوید Dockerfile Path برابر `Dockerfile` و Builder برابر Dockerfile است.
6. در Volumes، Volume موجود و داده‌دار را نگه دارید. برای این شاخه مسیر mount صحیح `/var/lib/marzban` است؛ دیتابیس و تنظیمات Xray در همین مسیرند. Volume را حذف، جایگزین یا خالی نکنید.
7. در Networking، دامنهٔ موجود را نگه دارید و Target Port را روی `8080` تنظیم کنید. پورت 8000 فقط upstream داخلی Uvicorn است؛ HTTPS عمومی Railway روی 443 خاتمه می‌یابد.
8. در Variables، مقادیر موجود را بی‌دلیل پاک یا بازنویسی نکنید. `ADMIN_PASSWORD` را فقط در Railway Variables به‌صورت Secret وارد کنید؛ آن را در GitHub یا چت قرار ندهید.
9. اگر دیتابیس قبلی از قبل مدیر دارد، رمز موجود حفظ می‌شود. برای تغییر رمز، فقط در صورت قصد قطعی مالک، `RESET_ADMIN_PASSWORD=1` را برای یک Deploy تنظیم کنید و بلافاصله پس از موفقیت حذفش کنید.
10. Deploy Latest Commit را اجرا کنید و Build Logs و Deploy Logs را تا پایان بررسی کنید.

## بررسی بعد از Deploy

- وضعیت Deploy باید SUCCESS/Active باشد.
- آدرس دامنه با مسیر `/health` باید پاسخ HTTP 200 بدهد.
- در لاگ‌ها نباید پیام عدم اتصال Volume یا خطای دیتابیس دیده شود.
- ورود مدیر باید با رمز موجود/تنظیم‌شده کار کند.
- یک کاربر آزمایشی بسازید و خروجی واقعی `/sub/<token>` را بررسی کنید.
- برای تأیید تونل واقعی، اشتراک را در v2rayNG روی یک شبکهٔ خارجی وارد کنید و اتصال و تبادل ترافیک را آزمایش کنید.

## نکتهٔ مهم

این شاخه در حال حاضر بر پایهٔ Marzban است، نه PasarGuard. مسیر Volume این دو یکی نیست. تغییر مسیر به `/var/lib/pasarguard` یا تعویض هسته بدون مهاجرت و پشتیبان‌گیری می‌تواند باعث از دسترس خارج‌شدن داده‌های فعلی شود.

ساخت یا موفقیت این Commit به‌تنهایی به معنی Deploy موفق، اتصال عمومی Xray یا تست موفق v2rayNG نیست. این موارد فقط پس از اجرای Deploy و آزمون واقعی قابل تأییدند.
