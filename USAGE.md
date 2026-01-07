Mini Shop (JSON prototype) — Quick Usage

Qisqacha:
- `add <id> <qty>` yoki `a <id> <qty>` yoki `1` — mahsulotni savatchaga qo'shish
- `buy <qty>` yoki `s <qty>` yoki `2` — mahsulotni to'g'ridan-to'g'ri sotib olish (quick buy)

Savatcha menyusida hozir faqat quyidagilar qabul qilinadi:
- `remove <product_id>` — savatchadan mahsulotni o'chirish
- `buy <product_id>` — savatchadagi mahsulotni to'liq sotib olish (savatchadan olib tashlanadi)
- `v <id>` yoki `view <id>` — mahsulot tafsilotini ko'rish
- `remove <id>` — savatchadan mahsulotni o'chirish
- `clear` — savatchani tozalash
- `checkout` — xaridni yakunlash (yetkazib berish yoki pickup tanlanadi)
- `h` yoki `help` — yordam ko'rsatish

Examples:
1) Ro'yxatdagi mahsulotni savatchaga qo'shish:
   - Kiriting: `2` ("Mahsulotlarni ko'rish" menyusida), so'ng: `add 3 2` — 3-id mahsulotdan 2 dona qo'shish.
2) Tez sotib olish (quick):
   - Kiriting: `2` (ro'yxat), so'ng faqat mahsulot ID: `1`, so'ng: `buy 1` — 1 dona sotib olinadi.

Note: Data lives under `data/*.json` (no database). Tests are under `tests/test_cli_flow.py`.

Login:
- Dastur ishga tushganda ism, pochta va parol so'raladi.
- Agar pochta mavjud bo'lsa va parol mos kelsa tizimga kirasiz; aks holda yangi hisob yaratiladi.
- Admin kirish uchun: `actamovyusuf007@gmail.com` / `luxnendo@890` — admin panel avtomatik ochiladi.
