import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
MEMBERSHIPS_FILE = os.path.join(DATA_DIR, "memberships.json")
PROMOTIONS_FILE = os.path.join(DATA_DIR, "promotions.json")
CART_FILE = os.path.join(DATA_DIR, "cart.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
SUPPORT_FILE = os.path.join(DATA_DIR, "support_messages.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

SHIPPING_FEE = 50.0

ADMIN_EMAIL = "actamovyusuf007@gmail.com"
ADMIN_PASSWORD = "luxnendo@890"


class DataManager:
    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class UserManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.current_user = None

    def load_users(self):
        if not os.path.exists(USERS_FILE):
            return []
        return self.data_manager.load_json(USERS_FILE)

    def save_users(self, users):
        self.data_manager.save_json(USERS_FILE, users)

    def find_user_by_email(self, email):
        if not email:
            return None
        users = self.load_users()
        elow = email.lower()
        for u in users:
            if u.get("email", "").lower() == elow:
                return u
        return None

    def hash_password(self, password, salt=None):
        import hashlib, binascii, os
        if salt is None:
            salt = os.urandom(16)
        elif isinstance(salt, str):
            salt = binascii.unhexlify(salt)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()

    def verify_password(self, password, salt_hex, hash_hex):
        import hashlib, binascii
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return binascii.hexlify(dk).decode() == hash_hex

    def set_user_password(self, user, password):
        salt, phash = self.hash_password(password)
        user.pop("password", None)
        user["password_hash"] = phash
        user["salt"] = salt

    def ensure_admin_user(self):
        users = self.load_users()
        if not any(u.get("email") == ADMIN_EMAIL for u in users):
            admin = {
                "name": "Admin",
                "email": ADMIN_EMAIL,
                "address": "",
                "orders": [],
                "is_admin": True
            }
            self.set_user_password(admin, ADMIN_PASSWORD)
            users.append(admin)
            self.save_users(users)

    def migrate_plain_passwords(self):
        users = self.load_users()
        changed = False
        for u in users:
            if u.get("password") and not u.get("password_hash"):
                self.set_user_password(u, u["password"])
                changed = True
        if changed:
            self.save_users(users)

    def change_password_flow(self):
        """Interactive password change flow.
        Asks for an email to confirm the account, then prompts for new password and confirmation.
        If the email exists among users, updates that user's password.
        """
        print("\n--- Parolni almashtirish ---")
        email = input("Tasdiqlash uchun email: ").strip()
        if not email:
            print("Email kiritilmadi.")
            return
        user = self.find_user_by_email(email)
        if not user:
            print("Bunday emailga ega foydalanuvchi topilmadi.")
            return
        # get new password twice
        while True:
            newpw = input("Yangi parol: ").strip()
            newpw2 = input("Yangi parolni tasdiqlang: ").strip()
            if not newpw:
                print("Parol bo'sh bo'lishi mumkin emas.")
                continue
            if newpw != newpw2:
                print("Parollar mos emas. Qayta urinib ko'ring.")
                continue
            self.set_user_password(user, newpw)
            users = self.load_users()
            for u in users:
                if u.get("email", "").lower() == user.get("email", "").lower():
                    u.update(user)
            self.save_users(users)
            print("Parol muvaffaqiyatli yangilandi.")
            return

    def login_prompt(self):
        self.migrate_plain_passwords()
        print("\n--- Kirish / Login ---")
        while True:
            name = input("Ism (b->chiqish): ").strip()
            if name.lower() in ("b", "back", "0"):
                print("Dasturdan chiqish uchun 0 ni bosing.")
                continue
            email = input("Pochta: ").strip()
            if not email or not name:
                print("Iltimos ism va pochta kiriting.")
                continue
            user = self.find_user_by_email(email)
            # password entry loop: re-prompt password only, and support 'change' keyword
            while True:
                password = input("Parol (yoki 'change' parolni almashtirish uchun, b->orqaga): ").strip()
                if password.lower() in ("b", "back", "0"):
                    # go back to ask name/email again
                    break
                if password.lower() == "change":
                    self.change_password_flow()
                    # reload user in case password was changed and continue prompting
                    user = self.find_user_by_email(email)
                    continue
                if not password:
                    print("Iltimos parol kiriting yoki 'change' yozing.")
                    continue
                # If no user found, create a new account using provided name/email/password
                if not user:
                    addr = input("Manzil (manzil kiriting): ").strip()
                    users = self.load_users()
                    new_user = {
                        "name": name,
                        "email": email,
                        "address": addr,
                        "orders": [],
                        "is_admin": False
                    }
                    self.set_user_password(new_user, password)
                    users.append(new_user)
                    self.save_users(users)
                    self.current_user = new_user
                    print(f"Hisob yaratildi va tizimga kirdingiz: {self.current_user.get('email')}")
                    return
                # existing user with hashed password
                if user.get("password_hash") and user.get("salt"):
                    if self.verify_password(password, user.get("salt"), user.get("password_hash")):
                        self.current_user = user
                        if user.get("is_admin"):
                            print(f"Admin sifatida tizimga kirdingiz: {user['email']}")
                            # admin_menu will be called from CLI
                            return "admin"
                        else:
                            print(f"Xush kelibsiz, {self.current_user.get('name')}!")
                        return
                    else:
                        print("Noto'g'ri parol. Iltimos qayta kiriting yoki 'change' yozing.")
                        continue
                # existing user with legacy plain password
                if user.get("password"):
                    if password == user.get("password"):
                        self.set_user_password(user, password)
                        users = self.load_users()
                        for u in users:
                            if u.get("email") == user.get("email"):
                                u.update(user)
                        self.save_users(users)
                        self.current_user = user
                        if user.get("is_admin"):
                            print(f"Admin sifatida tizimga kirdingiz: {user['email']}")
                            return "admin"
                        else:
                            print(f"Xush kelibsiz, {self.current_user.get('name')}!")
                        return
                    else:
                        print("Noto'g'ri parol. Iltimos qayta kiriting yoki 'change' yozing.")
                        continue
                # user exists but has no password info
                print("Bu foydalanuvchiga parol ma'lumotlari yo'q. Iltimos ro'yxatdan o'ting yoki 'change' deb parolni almashtiring.")
                # give user another chance to enter 'change' or go back
                continue


class ProductManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def find_product(self, prod_id):
        products = self.data_manager.load_json(PRODUCTS_FILE)
        for p in products:
            if p["id"] == prod_id:
                return p
        return None

    def list_categories(self):
        return self.data_manager.load_json(CATEGORIES_FILE)

    def list_products(self, category_id=None):
        products = self.data_manager.load_json(PRODUCTS_FILE)
        if category_id:
            products = [p for p in products if p.get("category_id") == category_id]
        return products

    def search_products(self, query):
        query = query.lower()
        return [p for p in self.data_manager.load_json(PRODUCTS_FILE) if query in p["name"].lower() or query in p.get("description", "").lower()]

    def show_memberships(self):
        return self.data_manager.load_json(MEMBERSHIPS_FILE)

    def get_promotions(self):
        return self.data_manager.load_json(PROMOTIONS_FILE)


class CartManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def load_cart(self):
        return self.data_manager.load_json(CART_FILE)

    def save_cart(self, cart):
        self.data_manager.save_json(CART_FILE, cart)

    def ask_confirm(self, prompt):
        ans = input(prompt).strip().lower()
        return ans in ("ha", "yes", "y")

    def add_to_cart(self, prod_id, qty, product_manager):
        # validation
        if qty <= 0:
            print("Soni musbat butun son bo'lishi kerak.")
            return
        product = product_manager.find_product(prod_id)
        if not product:
            print("Mahsulot topilmadi.")
            return
        if product.get("stock", 0) < qty:
            print(f"Yetarli stock yo'q. Mavjud: {product.get('stock')}")
            return
        # confirm
        if not self.ask_confirm(f"{product['name']} ni {qty} dona savatchaga qo'shishni tasdiqlaysizmi? (ha/no): "):
            print("Qo'shish bekor qilindi.")
            return
        cart = self.load_cart()
        # merge if exists
        for item in cart["items"]:
            if item["product_id"] == prod_id:
                item["qty"] += qty
                break
        else:
            cart["items"].append({
                "product_id": prod_id,
                "qty": qty,
                "unit_price": product["price"],
                "name": product["name"]
            })
        self.save_cart(cart)
        print("Mahsulot savatchaga qo'shildi.")

    def view_cart(self):
        cart = self.load_cart()
        if not cart["items"]:
            print("Savatcha bo'sh.")
            return
        total = 0.0
        print("Savatcha:")
        for it in cart["items"]:
            line = it["unit_price"] * it["qty"]
            total += line
            print(f"- [{it['product_id']}] {it['name']} x {it['qty']} = {line:.2f}")
        print(f"Jami: {total:.2f}")

    def clear_cart(self):
        if not self.load_cart()["items"]:
            print("Savatcha bo'sh.")
            return
        if self.ask_confirm("Savatchani tozalashni tasdiqlaysizmi? (ha/no): "):
            self.save_cart({"items": []})
            print("Savatcha tozalandi.")
        else:
            print("Amal bekor qilindi.")

    def remove_from_cart(self, prod_id):
        cart = self.load_cart()
        target = next((it for it in cart["items"] if it["product_id"] == prod_id), None)
        if not target:
            print("Mahsulot savatchada topilmadi.")
            return
        if self.ask_confirm(f"{target['name']} ni savatchadan o'chirishni tasdiqlaysizmi? (ha/no): "):
            cart["items"] = [it for it in cart["items"] if it["product_id"] != prod_id]
            self.save_cart(cart)
            print("Mahsulot savatchadan o'chirildi.")
        else:
            print("Amal bekor qilindi.")


class OrderManager:
    def __init__(self, data_manager, user_manager, product_manager, cart_manager):
        self.data_manager = data_manager
        self.user_manager = user_manager
        self.product_manager = product_manager
        self.cart_manager = cart_manager

    def get_user_orders(self, email):
        """Return list of orders for a given user email."""
        orders = self.data_manager.load_json(ORDERS_FILE)
        return [o for o in orders if o.get('user_email') == email]

    def view_my_orders(self):
        if not self.user_manager.current_user:
            print("Tizimga kirilmagan. Iltimos avval tizimga kiring.")
            return
        orders = self.get_user_orders(self.user_manager.current_user.get('email'))
        if not orders:
            print("Siz hali hech narsa sotib olmadingiz.")
            return
        print(f"\n--- {self.user_manager.current_user.get('name')} ning Xarid Tarixi ---")
        for o in orders:
            print(f"Buyurtma #{o['id']} - Jami: {o['total']:.2f} - Sana: {o.get('created_at')}")
            for it in o.get("items", []):
                print(f"  - {it.get('name')} x {it.get('qty')}")

    def compute_membership_effects(self, total, membership_id, qty=None, shipping_method=None):
        """Return a dict describing membership effects on the given order total.
        Keys: membership (dict or None), discount (float), total_after_discount (float),
        points_earned (int), priority_support (bool), free_shipping (bool), special_discount (float)
        """
        result = {
            "membership": None,
            "discount": 0.0,
            "total_after_discount": total,
            "points_earned": 0,
            "priority_support": False,
            "free_shipping": False,
            "special_discount": 0.0
        }
        if not membership_id:
            return result
        memberships = self.product_manager.show_memberships()
        mem = next((m for m in memberships if m["id"] == membership_id), None)
        if not mem:
            return result
        result["membership"] = mem
        # base discount
        base_discount = total * mem.get("discount_rate", 0.0)
        result["discount"] = base_discount
        # points
        points_mult = mem.get("points_multiplier", 1)
        result["points_earned"] = int(total * points_mult)
        # priority support
        result["priority_support"] = bool(mem.get("priority_support", False))
        # special business bulk pricing: if Business and qty provided and qty >= 10 give extra 10% off
        special = 0.0
        if mem.get("name", "").lower() == "business" and qty and qty >= 10:
            special = total * 0.10
            result["special_discount"] = special
            result["discount"] += special
        # total after discounts
        result["total_after_discount"] = max(total - result["discount"], 0.0)
        # free shipping: if membership has free_shipping_threshold and shipping_method is delivery
        threshold = mem.get("free_shipping_threshold")
        if shipping_method and shipping_method == "delivery" and threshold is not None:
            result["free_shipping"] = total >= float(threshold)
        return result

    def apply_membership_discount(self, total, membership_id, qty=None, shipping_method=None):
        """Backwards-compatible wrapper: return (total_after, discount_amount)
        Accepts optional qty and shipping_method to support business bulk pricing and free-shipping checks."""
        eff = self.compute_membership_effects(total, membership_id, qty=qty, shipping_method=shipping_method)
        return eff["total_after_discount"], eff["discount"]

    def apply_promo(self, total, code):
        if not code:
            return total, 0.0
        promos = self.product_manager.get_promotions()
        now = datetime.now().date()
        for p in promos:
            if p["code"].lower() == code.lower():
                start = datetime.strptime(p["start_date"], "%Y-%m-%d").date()
                end = datetime.strptime(p["end_date"], "%Y-%m-%d").date()
                if start <= now <= end:
                    if p["discount_type"] == "percent":
                        discount = total * (p["value"] / 100.0)
                    else:
                        discount = p["value"]
                    return max(total - discount, 0.0), discount
        print("Promo kod topilmadi yoki amal qilish muddati tugagan.")
        return total, 0.0

    def checkout(self):
        cart = self.cart_manager.load_cart()
        if not cart["items"]:
            print("Savatcha bo'sh. Avval mahsulot qo'shing.")
            return
        subtotal = sum(it["unit_price"] * it["qty"] for it in cart["items"])
        print(f"Subtotal: {subtotal:.2f}")
        # membership (if user already bought a membership, ask whether to use it)
        membership_id = None
        if self.user_manager.current_user and isinstance(self.user_manager.current_user, dict) and self.user_manager.current_user.get('membership_id'):
            use_mem = input("Sizda a'zolik mavjud. Chegirmadan foydalanasizmi? (ha/no): ").strip().lower()
            if use_mem in ("ha", "yes", "y"):
                membership_id = self.user_manager.current_user.get('membership_id')
        else:
            mem_choice = input("A'zolik ID (yoksa ENTER): ").strip()
            membership_id = int(mem_choice) if mem_choice.isdigit() else None
            if membership_id:
                mems = self.product_manager.show_memberships()
                if not any(m['id'] == membership_id for m in mems):
                    print("Bunday a'zolik topilmadi. A'zolik e'tiborga olinmaydi.")
                    membership_id = None
        qty_total = sum(it.get('qty', 0) for it in cart['items'])
        total_after_mem, mem_discount = self.apply_membership_discount(subtotal, membership_id, qty=qty_total)
        # display richer membership info
        mem_eff_preview = self.compute_membership_effects(subtotal, membership_id, qty=qty_total, shipping_method=None)
        print(f"A'zolik chegirmasi: {mem_discount:.2f} -> {total_after_mem:.2f}")
        if mem_eff_preview["points_earned"]:
            print(f"A'zolik ballari (kupon/ballar): {mem_eff_preview['points_earned']}")
        if mem_eff_preview["priority_support"]:
            print("Sizga ustuvor qo'llab-quvvatlash taqdim etiladi.")
        # promo
        promo_code = input("Promo kod (yoksa ENTER): ").strip()
        total_after_promo, promo_discount = self.apply_promo(total_after_mem, promo_code)
        print(f"Promo chegirma: {promo_discount:.2f} -> {total_after_promo:.2f}")
        # shipping
        while True:
            shipping_method = input("Yetkazib berish yoki pickup? (delivery/pickup): ").strip().lower()
            if shipping_method in ("delivery", "pickup"):
                break
            print("Iltimos 'delivery' yoki 'pickup' yozing.")
        shipping_fee = 0.0
        address = None
        if shipping_method == "delivery":
            while True:
                address = input("Yetkazib berish manzili (b->bekor qilish): ").strip()
                if not address:
                    print("Manzil bo'sh bo'lishi mumkin emas.")
                    continue
                if address.lower() in ("b", "back", "0"):
                    print("Checkout bekor qilindi.")
                    return
                break
            # recompute membership effects with shipping method to see if free shipping applies
            mem_eff = self.compute_membership_effects(subtotal, membership_id, qty=qty_total, shipping_method=shipping_method)
            if mem_eff["free_shipping"]:
                shipping_fee = 0.0
            else:
                shipping_fee = SHIPPING_FEE
        total = total_after_promo + shipping_fee
        print(f"Yakuniy to'lov: {total:.2f} (shipping: {shipping_fee:.2f})")
        confirm = input("Buyurtmani tasdiqlaysizmi? (ha/no): ").strip().lower()
        if confirm not in ("ha", "yes", "y"):
            print("Buyurtma bekor qilindi.")
            return
        # create order and update stocks
        orders = self.data_manager.load_json(ORDERS_FILE)
        order = {
            "id": len(orders) + 1,
            "items": cart["items"],
            "subtotal": subtotal,
            "membership_discount": mem_discount,
            "promo_discount": promo_discount,
            "shipping_fee": shipping_fee,
            "total": total,
            "shipping_method": shipping_method,
            "address": address,
            "user_email": self.user_manager.current_user.get("email") if self.user_manager.current_user else None,
            "user_name": self.user_manager.current_user.get("name") if self.user_manager.current_user else None,
            "created_at": datetime.now().isoformat()
        }
        # decrement stock
        products = self.data_manager.load_json(PRODUCTS_FILE)
        for it in cart["items"]:
            for p in products:
                if p["id"] == it["product_id"]:
                    p["stock"] = max(0, p.get("stock", 0) - it["qty"])
        self.data_manager.save_json(PRODUCTS_FILE, products)
        orders.append(order)
        self.data_manager.save_json(ORDERS_FILE, orders)
        # record order under user if logged in
        if self.user_manager.current_user:
            users = self.user_manager.load_users()
            u = next((x for x in users if x.get('email') == self.user_manager.current_user.get('email')), None)
            if u is not None:
                u.setdefault('orders', []).append(order['id'])
                self.user_manager.save_users(users)
        self.cart_manager.clear_cart()
        print(f"Buyurtma #{order['id']} qabul qilindi. Jami: {total:.2f}")

    def purchase_product_direct(self, prod_id, qty):
        product = self.product_manager.find_product(prod_id)
        if not product:
            print("Mahsulot topilmadi.")
            return False
        if qty <= 0:
            print("Soni musbat butun son bo'lishi kerak.")
            return False
        if product.get("stock", 0) < qty:
            print(f"Yetarli stock yo'q. Mavjud: {product.get('stock')}")
            return False
        subtotal = product["price"] * qty
        print(f"Subtotal: {subtotal:.2f}")
        # membership (if user already bought a membership, ask whether to use it)
        membership_id = None
        if self.user_manager.current_user and isinstance(self.user_manager.current_user, dict) and self.user_manager.current_user.get('membership_id'):
            use_mem = input("Sizda a'zolik mavjud. Chegirmadan foydalanasizmi? (ha/no): ").strip().lower()
            if use_mem in ("ha", "yes", "y"):
                membership_id = self.user_manager.current_user.get('membership_id')
        else:
            mem_choice = input("A'zolik ID (yoksa ENTER): ").strip()
            membership_id = int(mem_choice) if mem_choice.isdigit() else None
            if membership_id:
                mems = self.product_manager.show_memberships()
                if not any(m['id'] == membership_id for m in mems):
                    print("Bunday a'zolik topilmadi. A'zolik e'tiborga olinmaydi.")
                    membership_id = None
        total_after_mem, mem_discount = self.apply_membership_discount(subtotal, membership_id, qty=qty)
        mem_eff_preview = self.compute_membership_effects(subtotal, membership_id, qty=qty, shipping_method=None)
        print(f"A'zolik chegirmasi: {mem_discount:.2f} -> {total_after_mem:.2f}")
        if mem_eff_preview["points_earned"]:
            print(f"A'zolik ballari: {mem_eff_preview['points_earned']}")
        if mem_eff_preview["priority_support"]:
            print("Sizga ustuvor qo'llab-quvvatlash taqdim etiladi.")
        # promo
        promo_code = input("Promo kod (yoksa ENTER): ").strip()
        total_after_promo, promo_discount = self.apply_promo(total_after_mem, promo_code)
        print(f"Promo chegirma: {promo_discount:.2f} -> {total_after_promo:.2f}")
        # shipping
        while True:
            shipping_method = input("Yetkazib berish yoki pickup? (delivery/pickup): ").strip().lower()
            if shipping_method in ("delivery", "pickup"):
                break
            print("Iltimos 'delivery' yoki 'pickup' yozing.")
        shipping_fee = 0.0
        address = None
        if shipping_method == "delivery":
            while True:
                address = input("Yetkazib berish manzili (b->bekor qilish): ").strip()
                if not address:
                    print("Manzil bo'sh bo'lishi mumkin emas.")
                    continue
                if address.lower() in ("b", "back", "0"):
                    print("Buyurtma bekor qilindi.")
                    return False
                break
            # check membership free shipping for delivery
            mem_eff = self.compute_membership_effects(subtotal, membership_id, qty=qty, shipping_method=shipping_method)
            if mem_eff["free_shipping"]:
                shipping_fee = 0.0
            else:
                shipping_fee = SHIPPING_FEE
        total = total_after_promo + shipping_fee
        print(f"Yakuniy to'lov: {total:.2f} (shipping: {shipping_fee:.2f})")
        if not self.cart_manager.ask_confirm("Buyurtmani tasdiqlaysizmi? (ha/no): "):
            print("Buyurtma bekor qilindi.")
            return False
        orders = self.data_manager.load_json(ORDERS_FILE)
        order = {
            "id": len(orders) + 1,
            "items": [{
                "product_id": prod_id,
                "qty": qty,
                "unit_price": product["price"],
                "name": product["name"]
            }],
            "subtotal": subtotal,
            "membership_discount": mem_discount,
            "promo_discount": promo_discount,
            "shipping_fee": shipping_fee,
            "total": total,
            "shipping_method": shipping_method,
            "address": address,
            "user_email": self.user_manager.current_user.get("email") if self.user_manager.current_user else None,
            "user_name": self.user_manager.current_user.get("name") if self.user_manager.current_user else None,
            "created_at": datetime.now().isoformat()
        }
        products = self.data_manager.load_json(PRODUCTS_FILE)
        for p in products:
            if p["id"] == prod_id:
                p["stock"] = max(0, p.get("stock", 0) - qty)
        self.data_manager.save_json(PRODUCTS_FILE, products)
        orders.append(order)
        self.data_manager.save_json(ORDERS_FILE, orders)
        # record order under user if logged in
        if self.user_manager.current_user:
            users = self.user_manager.load_users()
            u = next((x for x in users if x.get('email') == self.user_manager.current_user.get('email')), None)
            if u is not None:
                u.setdefault('orders', []).append(order['id'])
                self.user_manager.save_users(users)
        print(f"Buyurtma #{order['id']} qabul qilindi. Jami: {total:.2f}")
        return True

    def purchase_membership(self, membership_id):
        """Allow the current user to purchase a membership package."""
        if not self.user_manager.current_user:
            print("Iltimos avval tizimga kiring.")
            return False
        mems = self.product_manager.show_memberships()
        mem = next((m for m in mems if m["id"] == membership_id), None)
        if not mem:
            print("Bunday a'zolik topilmadi.")
            return False
        price = float(mem.get("price", 0.0))
        print(f"Paket: {mem['name']} - Narx: {price:.2f}")
        if not self.cart_manager.ask_confirm("Sotib olishni tasdiqlaysizmi? (ha/no): "):
            print("Sotib olish bekor qilindi.")
            return False
        orders = self.data_manager.load_json(ORDERS_FILE)
        order = {
            "id": len(orders) + 1,
            "items": [{
                "membership_id": membership_id,
                "qty": 1,
                "unit_price": price,
                "name": f"Membership: {mem['name']}"
            }],
            "subtotal": price,
            "membership_discount": 0.0,
            "promo_discount": 0.0,
            "shipping_fee": 0.0,
            "total": price,
            "shipping_method": "membership",
            "address": None,
            "user_email": self.user_manager.current_user.get("email") if self.user_manager.current_user else None,
            "user_name": self.user_manager.current_user.get("name") if self.user_manager.current_user else None,
            "created_at": datetime.now().isoformat()
        }
        orders.append(order)
        self.data_manager.save_json(ORDERS_FILE, orders)
        # mark membership on user record (persist and in-memory)
        users = self.user_manager.load_users()
        u = next((x for x in users if x.get('email') == self.user_manager.current_user.get('email')), None)
        if u is not None:
            u['membership_id'] = membership_id
            self.user_manager.save_users(users)
            # update in-memory user
            self.user_manager.current_user['membership_id'] = membership_id
        print("A'zolik muvaffaqiyatli sotib olindi.")
        return True

    def purchase_from_cart(self, prod_id):
        """Purchase a product from the cart by its product id. Returns True on success."""
        cart = self.cart_manager.load_cart()
        item = next((it for it in cart["items"] if it["product_id"] == prod_id), None)
        if not item:
            print("Mahsulot savatchada topilmadi.")
            return False
        qty = item["qty"]
        ok = self.purchase_product_direct(prod_id, qty)
        if ok:
            cart["items"] = [it for it in cart["items"] if it["product_id"] != prod_id]
            self.cart_manager.save_cart(cart)
            print("Mahsulot savatchadan sotib olindi va savatchadan o'chirildi.")
            return True
        else:
            print("Sotib olish bekor qilindi yoki muvaffaqiyatsiz tugadi.")
            return False


class CLI:
    def __init__(self):
        self.data_manager = DataManager()
        self.user_manager = UserManager(self.data_manager)
        self.product_manager = ProductManager(self.data_manager)
        self.cart_manager = CartManager(self.data_manager)
        self.order_manager = OrderManager(self.data_manager, self.user_manager, self.product_manager, self.cart_manager)

    def normalize_cmd_parts(self, parts):
        """Normalize the first token in split parts to short canonical commands.
        'add' -> 'a', 'a' -> 'a', 'buy'|'s'|'sotib' -> 's', 'v' -> 'v', 'b'|'back'|'0' -> 'b'
        """
        if not parts:
            return
        tok = parts[0].lower()
        if tok in ("add", "a"):
            parts[0] = "a"
        elif tok in ("buy", "s", "sotib"):
            parts[0] = "s"
        elif tok in ("v", "view"):
            parts[0] = "v"
        elif tok in ("b", "back", "0"):
            parts[0] = "b"
        else:
            parts[0] = tok

    def admin_menu(self):
        while True:
            print("\n--- Admin panel ---")
            print("1. Barcha foydalanuvchilar")
            print("2. Mahsulotlar: sotilgan / sotilmagan")
            print("3. Barcha buyurtmalar (xaridlar tarixi)")
            print("4. Mahsulot qo'shish")
            print("0. Orqaga (logout)")
            choice = input("Tanlov: ").strip()
            if choice == "1":
                users = self.user_manager.load_users()
                for u in users:
                    print(f"\n- {u.get('name')} <{u.get('email')}>")
                    print(f"  Manzil: {u.get('address')}")
                    # gather orders for user
                    user_orders = self.order_manager.get_user_orders(u.get('email'))
                    if not user_orders:
                        print("  Xarid qilgan narsasi: Yo'q")
                    else:
                        print("  Xaridlar:")
                        for o in user_orders:
                            print(f"    Buyurtma #{o['id']} - Jami: {o['total']:.2f} - Sana: {o.get('created_at')}")
                            for it in o.get("items", []):
                                print(f"      - {it.get('name')} x {it.get('qty')}")
            elif choice == "2":
                products = self.data_manager.load_json(PRODUCTS_FILE)
                orders = self.data_manager.load_json(ORDERS_FILE)
                sold_counts = {}
                for o in orders:
                    for it in o.get("items", []):
                        sold_counts[it["product_id"]] = sold_counts.get(it["product_id"], 0) + it.get("qty", 0)
                print("\nSotilgan mahsulotlar:")
                for p in products:
                    if p["id"] in sold_counts:
                        print(f"- [{p['id']}] {p['name']} sold: {sold_counts[p['id']]} (stock left: {p.get('stock')})")
                print("\nSotilmagan mahsulotlar:")
                for p in products:
                    if p["id"] not in sold_counts:
                        print(f"- [{p['id']}] {p['name']} (stock: {p.get('stock')})")

            elif choice == "3":
                orders = self.data_manager.load_json(ORDERS_FILE)
                if not orders:
                    print("Buyurtma topilmadi.")
                else:
                    print("\n--- Barcha buyurtmalar (xaridlar tarixi) ---")
                    for o in orders:
                        buyer = self.user_manager.find_user_by_email(o.get('user_email')) or {}
                        print(f"Buyurtma #{o['id']} - Jami: {o.get('total'):.2f} - Sana: {o.get('created_at')}")
                        print(f"  Xaridor: {buyer.get('name')} <{buyer.get('email')}>")
                        print(f"  Manzil: {buyer.get('address')}")
                        for it in o.get('items', []):
                            print(f"    - {it.get('name')} x {it.get('qty')}")
            elif choice == "4":
                # Add new product (admin-only)
                print("\n--- Yangi mahsulot qo'shish ---")
                name = input("Mahsulot nomi: ").strip()
                if not name:
                    print("Mahsulot nomi bo'sh. Bekor qilindi.")
                    continue
                price_str = input("Narxi (raqam): ").strip()
                try:
                    price = float(price_str)
                    if price < 0:
                        raise ValueError()
                except Exception:
                    print("Noto'g'ri narx. Bekor qilindi.")
                    continue
                type_input = input("Turi (kategoriya id yoki nom, ENTER bo'sh): ").strip()
                stock_str = input("Boshlang'ich stock (raqam, default 0): ").strip()
                if stock_str:
                    if not stock_str.isdigit():
                        print("Noto'g'ri stock. Bekor qilindi.")
                        continue
                    stock = int(stock_str)
                else:
                    stock = 0
                products = self.data_manager.load_json(PRODUCTS_FILE)
                new_id = max((p.get('id', 0) for p in products), default=0) + 1
                new_prod = {"id": new_id, "name": name, "price": price, "stock": stock}
                if type_input:
                    if type_input.isdigit():
                        new_prod['category_id'] = int(type_input)
                    else:
                        new_prod['type'] = type_input
                products.append(new_prod)
                self.data_manager.save_json(PRODUCTS_FILE, products)
                print(f"Mahsulot qo'shildi: [{new_prod['id']}] {new_prod['name']} - {new_prod['price']:.2f} (stock: {new_prod['stock']})")
            elif choice in ("0", "b", "back", "logout"):
                print("Admin paneldan chiqildi.")
                return
            else:
                print("Noto'g'ri tanlov.")

    def send_support_message(self):
        while True:
            name = input("Ismingiz (b->orqaga): ").strip()
            if name.lower() in ("b", "back", "0") or not name:
                print("Bekor qilindi.")
                return
            email = input("Email: ").strip()
            if not email:
                print("Email bo'sh bo'lishi mumkin emas.")
                continue
            subject = input("Mavzu: ").strip()
            message = input("Xabar: ").strip()
            if not message:
                print("Xabar bo'sh bo'lishi mumkin emas.")
                continue
            if not self.cart_manager.ask_confirm("Xabarni yuborasizmi? (ha/no): "):
                print("Bekor qilindi.")
                return
            msgs = self.data_manager.load_json(SUPPORT_FILE)
            msgs.append({
                "id": len(msgs) + 1,
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
                "status": "new",
                "created_at": datetime.now().isoformat()
            })
            self.data_manager.save_json(SUPPORT_FILE, msgs)
            print("Xabaringiz qabul qilindi. Tez orada javob beramiz.")
            return

    def print_main(self):
        print("\n=== Tech House===")
        if self.user_manager.current_user:
            role = " (admin)" if self.user_manager.current_user.get("is_admin") else ""
            print(f"Logged in as: {self.user_manager.current_user.get('name')} <{self.user_manager.current_user.get('email')}>{role}")
        print("1. Toifalarni ko'rish")
        print("2. Mahsulotlarni ko'rish (barcha)")
        print("3. Toifaga ko'ra mahsulotlar")
        print("4. Mahsulot qidirish")
        print("5. Mahsulot tafsiloti")
        print("6. A'zolik paketlari")
        print("7. Savatchaga qo'shish")
        print("8. Savatchani ko'rish")
        print("9. Buyurtma berish (checkout)")
        print("10. Qo'llab‑quvvatlashga xabar yuborish")
        print("11. Mening xaridlarim")
        print("0. Chiqish")
        print("h. Yordam / Help")

    def print_help(self):
        print("\n--- Yordam / Help ---")
        print("Qisqacha buyruqlar:")
        print("- 'add <id> <qty>' yoki 'a <id> <qty>' yoki '1' — mahsulotni savatchaga qo'shish")
        print("- 'buy <qty>' yoki 's <qty>' yoki '2' — mahsulotni birlamchi sotib olish (quick)")
        print("- 'v <id>' yoki 'view <id>' — mahsulot tafsilotini ko'rish")
        print("- 'remove <id>' — savatchadan o'chirish")
        print("- 'clear' — savatchani tozalash")
        print("- 'checkout' — xaridni yakunlash")
        print("- 'h' yoki 'help' — bu yordam ekranini ko'rsatish")
        print("\nLogin:\n- Dastur ishga tushganda ism, pochta va parol so'raladi. Agar pochta mavjud bo'lsa teskari parol bilan tizimga kiriladi; aks holda hisob yaratiladi.")
        print("- Admin uchun: email = actamovyusuf007@gmail.com, parol = luxnendo@890")
        print("- Tizimdan chiqish uchun menyuda 'logout' deb yozing.")
        print("---")

    def main(self):
        # ensure data dir exists
        os.makedirs(DATA_DIR, exist_ok=True)
        # ensure cart exists
        if not os.path.exists(CART_FILE):
            self.data_manager.save_json(CART_FILE, {"items": []})
        # ensure users file exists and admin is present
        if not os.path.exists(USERS_FILE):
            self.data_manager.save_json(USERS_FILE, [])
        self.user_manager.ensure_admin_user()
        # ask user to login before showing main menu
        login_result = self.user_manager.login_prompt()
        if login_result == "admin":
            self.admin_menu()
        while True:
            self.print_main()
            cmd = input("Tanlov (yoki 'logout' qayta kirish uchun): ").strip()
            if cmd.lower() == 'logout':
                print("Siz tizimdan chiqdingiz. Yana kirish uchun ma'lumot kiriting.")
                login_result = self.user_manager.login_prompt()
                if login_result == "admin":
                    self.admin_menu()
                continue
            if cmd == "0":
                print("Xayr!")
                break
            # 1) Categories submenu
            if cmd == "1":
                while True:
                    cats = self.product_manager.list_categories()
                    for c in cats:
                        print(f"{c['id']}. {c['name']}")
                    sub = input("Toifa ID (id->ko'rish, b->orqaga): ").strip()
                    if sub.lower() in ("b", "back", "0") or not sub:
                        break
                    if sub.isdigit():
                        
                        cid = int(sub)
                        while True:
                            prods = self.product_manager.list_products(cid)
                            if not prods:
                                print("Bu toifada mahsulot yo'q.")
                            else:
                                for p in prods:
                                    print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                            act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                            if act.lower() in ("b", "back", "0") or not act:
                                break
                            parts = act.split()
                            self.normalize_cmd_parts(parts)
                            if parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                                pid = int(parts[1])
                                prod = self.product_manager.find_product(pid)
                                if not prod:
                                    print("Mahsulot topilmadi.")
                                else:
                                    print(json.dumps(prod, ensure_ascii=False, indent=2))
                                    choice = input("[add <qty> | buy <qty> | b]: ").strip()
                                    cparts = choice.split()
                                    self.normalize_cmd_parts(cparts)
                                    if not cparts:
                                        continue
                                    if cparts[0].lower() == 'a':
                                        if len(cparts) >= 2 and cparts[1].isdigit():
                                            self.cart_manager.add_to_cart(pid, int(cparts[1]), self.product_manager)
                                        else:
                                            qty = input("Soni: ").strip()
                                            if qty.isdigit():
                                                self.cart_manager.add_to_cart(pid, int(qty), self.product_manager)
                                            else:
                                                print("Noto'g'ri son. Qo'shish bekor qilindi.")
                                    elif cparts[0].lower() in ('s', 'buy', 'sotib'):
                                        if len(cparts) >= 2 and cparts[1].isdigit():
                                            self.order_manager.purchase_product_direct(pid, int(cparts[1]))
                                        else:
                                            qty = input("Soni: ").strip()
                                            if qty.isdigit():
                                                self.order_manager.purchase_product_direct(pid, int(qty))
                                            else:
                                                print("Noto'g'ri son. Sotib olish bekor qilindi.")
                                    elif cparts[0].lower() in ('b', 'back', '0'):
                                        continue
                                    else:
                                        print("Noto'g'ri tanlov.")
                            elif parts[0].lower() in ('a','add'):
                                # support 'add <id>' or 'add    <id>' or 'add' -> prompt for missing info
                                if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                                    self.cart_manager.add_to_cart(int(parts[1]), int(parts[2]), self.product_manager)
                                elif len(parts) >= 2 and parts[1].isdigit():
                                    qty = input("Soni: ").strip()
                                    if qty.isdigit():
                                        self.cart_manager.add_to_cart(int(parts[1]), int(qty), self.product_manager)
                                    else:
                                        print("Noto'g'ri son. Qo'shish bekor qilindi.")
                                else:
                                    pid = input("Mahsulot ID: ").strip()
                                    if not pid.isdigit():
                                        print("Noto'g'ri ID. Bekor qilindi.")
                                    else:
                                        qty = input("Soni: ").strip()
                                        if qty.isdigit():
                                            self.cart_manager.add_to_cart(int(pid), int(qty), self.product_manager)
                                        else:
                                            print("Noto'g'ri son. Qo'shish bekor qilindi.")
                            else:
                                print("Noto'g'ri tanlov.")
            # 2) All products 
            elif cmd == "2":
                while True:
                    for p in self.product_manager.list_products():
                        print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                    act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                    if act.lower() in ("b", "back", "0") or not act:
                        break
                    parts = act.split()
                    self.normalize_cmd_parts(parts)
                    if len(parts) == 1 and parts[0].isdigit():
                        pid = int(parts[0])
                        prod = self.product_manager.find_product(pid)
                        if not prod:
                            print("Mahsulot topilmadi.")
                            continue
                        # show product details first
                        print(json.dumps(prod, ensure_ascii=False, indent=2))
                        choice = input("[1:add | 2:buy | b]: ").strip()
                        cparts = choice.split()
                        self.normalize_cmd_parts(cparts)
                        if not cparts:
                            continue
                        token = cparts[0].lower()
                        if token == 'a' or token == '1':
                            if len(cparts) >= 2 and cparts[1].isdigit():
                                self.cart_manager.add_to_cart(pid, int(cparts[1]), self.product_manager)
                            else:
                                qty = input("Soni: ").strip()
                                if qty.isdigit():
                                    self.cart_manager.add_to_cart(pid, int(qty), self.product_manager)
                                else:
                                    print("Noto'g'ri son. Qo'shish bekor qilindi.")
                        elif token in ('s', 'buy', 'sotib') or token == '2':
                            if len(cparts) >= 2 and cparts[1].isdigit():
                                self.order_manager.purchase_product_direct(pid, int(cparts[1]))
                            else:
                                qty = input("Soni: ").strip()
                                if qty.isdigit():
                                    self.order_manager.purchase_product_direct(pid, int(qty))
                                else:
                                    print("Noto'g'ri son. Sotib olish bekor qilindi.")
                        elif token in ('b', 'back', '0'):
                            continue
                        else:
                            print("Noto'g'ri tanlov.")
                    elif parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                        p = self.product_manager.find_product(int(parts[1]))
                        if p:
                            print(json.dumps(p, ensure_ascii=False, indent=2))
                        else:
                            print("Mahsulot topilmadi.")
                    elif parts[0].lower() == 'a' and len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                        self.cart_manager.add_to_cart(int(parts[1]), int(parts[2]), self.product_manager)
                    else:
                        print("Noto'g'ri tanlov.")
            # 3) Products by category
            elif cmd == "3":
                while True:
                    cid = input("Toifa ID (b->orqaga): ").strip()
                    if cid.lower() in ("b", "back", "0") or not cid:
                        break
                    if cid.isdigit():
                        cid = int(cid)
                        while True:
                            prods = self.product_manager.list_products(cid)
                            if not prods:
                                print("Bu toifada mahsulot yo'q.")
                            else:
                                for p in prods:
                                    print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                            act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                            if act.lower() in ("b", "back", "0") or not act:
                                break
                            parts = act.split()
                            self.normalize_cmd_parts(parts)
                            # if user types only a product id, show quick actions
                            if len(parts) == 1 and parts[0].isdigit():
                                pid = int(parts[0])
                                prod = self.product_manager.find_product(pid)
                                if not prod:
                                    print("Mahsulot topilmadi.")
                                    continue
                                # show product details first
                                print(json.dumps(prod, ensure_ascii=False, indent=2))
                                choice = input("[add <qty> qo'shish | buy <qty> sotib olish | v ko'rish | b orqaga]: ").strip()
                                cparts = choice.split()
                                self.normalize_cmd_parts(cparts)
                                if not cparts:
                                    continue
                                if cparts[0].lower() == 'v':
                                    print(json.dumps(prod, ensure_ascii=False, indent=2))
                                elif cparts[0].lower() in ('a', 'add'):
                                    if len(cparts) >= 2 and cparts[1].isdigit():
                                        self.cart_manager.add_to_cart(pid, int(cparts[1]), self.product_manager)
                                    else:
                                        qty = input("Soni: ").strip()
                                        if qty.isdigit():
                                            self.cart_manager.add_to_cart(pid, int(qty), self.product_manager)
                                        else:
                                            print("Noto'g'ri son. Qo'shish bekor qilindi.")
                                elif cparts[0].lower() in ('s', 'buy', 'sotib'):
                                    if len(cparts) >= 2 and cparts[1].isdigit():
                                        self.order_manager.purchase_product_direct(pid, int(cparts[1]))
                                    else:
                                        qty = input("Soni: ").strip()
                                        if qty.isdigit():
                                            self.order_manager.purchase_product_direct(pid, int(qty))
                                        else:
                                            print("Noto'g'ri son. Sotib olish bekor qilindi.")
                                else:
                                    print("Noto'g'ri tanlov.")
                            else:
                                print("Mahsulot topilmadi.")
            # 4) Search products
            elif cmd == "4":
                query = input("Qidiruv so'zi: ").strip()
                if query:
                    results = self.product_manager.search_products(query)
                    if results:
                        print("Natijalar:")
                        for p in results:
                            print(f"{p['id']}. {p['name']} - {p['price']:.2f}")
                    else:
                        print("Hech narsa topilmadi.")
            # 5) Product details
            elif cmd == "5":
                pid = input("Mahsulot ID: ").strip()
                if pid.isdigit():
                    prod = self.product_manager.find_product(int(pid))
                    if prod:
                        print(json.dumps(prod, ensure_ascii=False, indent=2))
                    else:
                        print("Mahsulot topilmadi.")
            # 6) Memberships
            elif cmd == "6":
                while True:
                    print("\n--- A'zolik paketlari ---")
                    for m in self.product_manager.show_memberships():
                        thr = m.get('free_shipping_threshold')
                        thr_text = f"bepul yetkazib berish >= {thr:.2f}" if thr is not None else "bepul yetkazib berish: yo'q"
                        print(f"{m['id']}. {m['name']} - chegirma: {m.get('discount_rate',0)*100:.0f}% | ballar koeff: {m.get('points_multiplier')} | ustuvor: {m.get('priority_support')} | {thr_text} | narx: {m.get('price',0):.2f}")
                    sub = input("Paket ID sotib olish uchun kiriting yoki b->orqaga: ").strip()
                    if sub.lower() in ('b','back','0','') or not sub:
                        break
                    if sub.isdigit():
                        mid = int(sub)
                        if self.order_manager.purchase_membership(mid):
                            users = self.user_manager.load_users()
                            u = next((x for x in users if x.get('email') == self.user_manager.current_user.get('email')), None)
                            if u is not None and isinstance(self.user_manager.current_user, dict):
                                self.user_manager.current_user.clear()
                                self.user_manager.current_user.update(u)
                            print("A'zolik sotib olindi. Asosiy menyuga qaytilmoqda.")
                            break
                    else:
                        print("Noto'g'ri tanlov.")
            # 7) Add to cart 
            elif cmd == "7":
                while True:
                    pid = input("Mahsulot ID (b->orqaga): ").strip()
                    if pid.lower() in ("b", "back", "0") or not pid:
                        break
                    qty = input("Soni: ").strip()
                    if pid.isdigit() and qty.isdigit():
                        self.cart_manager.add_to_cart(int(pid), int(qty), self.product_manager)
                    else:
                        print("Noto'g'ri kirish.")
            # 8) Cart menu
            elif cmd == "8":
                while True:
                    self.cart_manager.view_cart()
                    act = input("[remove <product_id> | buy <product_id> | b orqaga]: ").strip()
                    if act.lower() in ("b", "back", "0") or not act:
                        break
                    parts = act.split()
                    if parts[0].lower() == 'remove' and len(parts) >= 2 and parts[1].isdigit():
                        self.cart_manager.remove_from_cart(int(parts[1]))
                    elif parts[0].lower() in ('buy', 's', 'sotib') and len(parts) >= 2 and parts[1].isdigit():
                        pid = int(parts[1])
                        self.order_manager.purchase_from_cart(pid)
                    else:
                        print("Noto'g'ri tanlov. Faqat 'remove <id>' yoki 'buy <id>' qabul qilinadi.")
            # 9) Checkout 
            elif cmd == "9":
                while True:
                    self.order_manager.checkout()
                    again = input("Yana buyurtma berasizmi? (ha->yana / b->menyuga qaytish): ").strip().lower()
                    if again in ("b", "back", "0", "no"):
                        break
            # 10) Support
            elif cmd == "10":
                while True:
                    sub = input("[s->xabar yuborish | b->orqaga]: ").strip().lower()
                    if sub in ("b", "back", "0") or not sub:
                        break
                    if sub == 's':
                        self.send_support_message()
                    else:
                        print("Noto'g'ri tanlov.")
            # 11) View my orders
            elif cmd == "11":
                self.order_manager.view_my_orders()
            elif cmd.lower() in ('h', 'help', '?'):
                self.print_help()
                continue
            elif cmd == "0":
                print("Xayr!")
                break
            else:
                print("Noto'g'ri tanlov. Iltimos menyudan amallarni tanlang yoki yordam uchun dokumentatsiyaga murojaat qiling.")


if __name__ == '__main__':
    try:
        cli = CLI()
        cli.main()
    except (KeyboardInterrupt, SystemExit):
        print("\nDastur yopildi.")
    except Exception:
        print("\nDastur yopildi.")

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    return load_json(USERS_FILE)


def save_users(users):
    save_json(USERS_FILE, users)


def find_user_by_email(email):
    if not email:
        return None
    users = load_users()
    elow = email.lower()
    for u in users:
        if u.get("email", "").lower() == elow:
            return u
    return None


def change_password_flow():
    """Interactive password change flow.
    Asks for an email to confirm the account, then prompts for new password and confirmation.
    If the email exists among users, updates that user's password.
    """
    print("\n--- Parolni almashtirish ---")
    email = input("Tasdiqlash uchun email: ").strip()
    if not email:
        print("Email kiritilmadi.")
        return
    user = find_user_by_email(email)
    if not user:
        print("Bunday emailga ega foydalanuvchi topilmadi.")
        return
    # get new password twice
    while True:
        newpw = input("Yangi parol: ").strip()
        newpw2 = input("Yangi parolni tasdiqlang: ").strip()
        if not newpw:
            print("Parol bo'sh bo'lishi mumkin emas.")
            continue
        if newpw != newpw2:
            print("Parollar mos emas. Qayta urinib ko'ring.")
            continue
        set_user_password(user, newpw)
        users = load_users()
        for u in users:
            if u.get("email", "").lower() == user.get("email", "").lower():
                u.update(user)
        save_users(users)
        print("Parol muvaffaqiyatli yangilandi.")
        return


# --- Password hashing ---
def hash_password(password, salt=None):
    import hashlib, binascii, os
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = binascii.unhexlify(salt)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()


def verify_password(password, salt_hex, hash_hex):
    import hashlib, binascii
    salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return binascii.hexlify(dk).decode() == hash_hex


def set_user_password(user, password):
    salt, phash = hash_password(password)
    user.pop("password", None)
    user["password_hash"] = phash
    user["salt"] = salt


def ensure_admin_user():
    users = load_users()
    if not any(u.get("email") == ADMIN_EMAIL for u in users):
        admin = {
            "name": "Admin",
            "email": ADMIN_EMAIL,
            "address": "",
            "orders": [],
            "is_admin": True
        }
        set_user_password(admin, ADMIN_PASSWORD)
        users.append(admin)
        save_users(users)


def migrate_plain_passwords():
    users = load_users()
    changed = False
    for u in users:
        if u.get("password") and not u.get("password_hash"):
            set_user_password(u, u["password"])
            changed = True
    if changed:
        save_users(users)


def login_prompt():
    global CURRENT_USER
    migrate_plain_passwords()
    print("\n--- Kirish / Login ---")
    while True:
        name = input("Ism (b->chiqish): ").strip()
        if name.lower() in ("b", "back", "0"):
            print("Dasturdan chiqish uchun 0 ni bosing.")
            continue
        email = input("Pochta: ").strip()
        if not email or not name:
            print("Iltimos ism va pochta kiriting.")
            continue
        user = find_user_by_email(email)
        # password entry loop: re-prompt password only, and support 'change' keyword
        while True:
            password = input("Parol (yoki 'change' parolni almashtirish uchun, b->orqaga): ").strip()
            if password.lower() in ("b", "back", "0"):
                # go back to ask name/email again
                break
            if password.lower() == "change":
                change_password_flow()
                # reload user in case password was changed and continue prompting
                user = find_user_by_email(email)
                continue
            if not password:
                print("Iltimos parol kiriting yoki 'change' yozing.")
                continue
            # If no user found, create a new account using provided name/email/password
            if not user:
                addr = input("Manzil (manzil kiriting): ").strip()
                users = load_users()
                new_user = {
                    "name": name,
                    "email": email,
                    "address": addr,
                    "orders": [],
                    "is_admin": False
                }
                set_user_password(new_user, password)
                users.append(new_user)
                save_users(users)
                CURRENT_USER = new_user
                print(f"Hisob yaratildi va tizimga kirdingiz: {CURRENT_USER.get('email')}")
                return
            # existing user with hashed password
            if user.get("password_hash") and user.get("salt"):
                if verify_password(password, user.get("salt"), user.get("password_hash")):
                    CURRENT_USER = user
                    if user.get("is_admin"):
                        print(f"Admin sifatida tizimga kirdingiz: {user['email']}")
                        admin_menu()
                    else:
                        print(f"Xush kelibsiz, {CURRENT_USER.get('name')}!")
                    return
                else:
                    print("Noto'g'ri parol. Iltimos qayta kiriting yoki 'change' yozing.")
                    continue
            # existing user with legacy plain password
            if user.get("password"):
                if password == user.get("password"):
                    set_user_password(user, password)
                    users = load_users()
                    for u in users:
                        if u.get("email") == user.get("email"):
                            u.update(user)
                    save_users(users)
                    CURRENT_USER = user
                    if user.get("is_admin"):
                        print(f"Admin sifatida tizimga kirdingiz: {user['email']}")
                        admin_menu()
                    else:
                        print(f"Xush kelibsiz, {CURRENT_USER.get('name')}!")
                    return
                else:
                    print("Noto'g'ri parol. Iltimos qayta kiriting yoki 'change' yozing.")
                    continue
            # user exists but has no password info
            print("Bu foydalanuvchiga parol ma'lumotlari yo'q. Iltimos ro'yxatdan o'ting yoki 'change' deb parolni almashtiring.")
            # give user another chance to enter 'change' or go back
            continue


def admin_menu():
    while True:
        print("\n--- Admin panel ---")
        print("1. Barcha foydalanuvchilar")
        print("2. Mahsulotlar: sotilgan / sotilmagan")
        print("3. Barcha buyurtmalar (xaridlar tarixi)")
        print("4. Mahsulot qo'shish")
        print("0. Orqaga (logout)")
        choice = input("Tanlov: ").strip()
        if choice == "1":
            users = load_users()
            for u in users:
                print(f"\n- {u.get('name')} <{u.get('email')}>")
                print(f"  Manzil: {u.get('address')}")
                # gather orders for user
                user_orders = get_user_orders(u.get('email'))
                if not user_orders:
                    print("  Xarid qilgan narsasi: Yo'q")
                else:
                    print("  Xaridlar:")
                    for o in user_orders:
                        print(f"    Buyurtma #{o['id']} - Jami: {o['total']:.2f} - Sana: {o.get('created_at')}")
                        for it in o.get("items", []):
                            print(f"      - {it.get('name')} x {it.get('qty')}")
        elif choice == "2":
            products = load_json(PRODUCTS_FILE)
            orders = load_json(ORDERS_FILE)
            sold_counts = {}
            for o in orders:
                for it in o.get("items", []):
                    sold_counts[it["product_id"]] = sold_counts.get(it["product_id"], 0) + it.get("qty", 0)
            print("\nSotilgan mahsulotlar:")
            for p in products:
                if p["id"] in sold_counts:
                    print(f"- [{p['id']}] {p['name']} sold: {sold_counts[p['id']]} (stock left: {p.get('stock')})")
            print("\nSotilmagan mahsulotlar:")
            for p in products:
                if p["id"] not in sold_counts:
                    print(f"- [{p['id']}] {p['name']} (stock: {p.get('stock')})")

        elif choice == "3":
            orders = load_json(ORDERS_FILE)
            if not orders:
                print("Buyurtma topilmadi.")
            else:
                print("\n--- Barcha buyurtmalar (xaridlar tarixi) ---")
                for o in orders:
                    buyer = find_user_by_email(o.get('user_email')) or {}
                    print(f"Buyurtma #{o['id']} - Jami: {o.get('total'):.2f} - Sana: {o.get('created_at')}")
                    print(f"  Xaridor: {buyer.get('name')} <{buyer.get('email')}>")
                    print(f"  Manzil: {buyer.get('address')}")
                    for it in o.get('items', []):
                        print(f"    - {it.get('name')} x {it.get('qty')}")
        elif choice == "4":
            # Add new product (admin-only)
            print("\n--- Yangi mahsulot qo'shish ---")
            name = input("Mahsulot nomi: ").strip()
            if not name:
                print("Mahsulot nomi bo'sh. Bekor qilindi.")
                continue
            price_str = input("Narxi (raqam): ").strip()
            try:
                price = float(price_str)
                if price < 0:
                    raise ValueError()
            except Exception:
                print("Noto'g'ri narx. Bekor qilindi.")
                continue
            type_input = input("Turi (kategoriya id yoki nom, ENTER bo'sh): ").strip()
            stock_str = input("Boshlang'ich stock (raqam, default 0): ").strip()
            if stock_str:
                if not stock_str.isdigit():
                    print("Noto'g'ri stock. Bekor qilindi.")
                    continue
                stock = int(stock_str)
            else:
                stock = 0
            products = load_json(PRODUCTS_FILE)
            new_id = max((p.get('id', 0) for p in products), default=0) + 1
            new_prod = {"id": new_id, "name": name, "price": price, "stock": stock}
            if type_input:
                if type_input.isdigit():
                    new_prod['category_id'] = int(type_input)
                else:
                    new_prod['type'] = type_input
            products.append(new_prod)
            save_json(PRODUCTS_FILE, products)
            print(f"Mahsulot qo'shildi: [{new_prod['id']}] {new_prod['name']} - {new_prod['price']:.2f} (stock: {new_prod['stock']})")
        elif choice in ("0", "b", "back", "logout"):
            print("Admin paneldan chiqildi.")
            return
        else:
            print("Noto'g'ri tanlov.")


def get_user_orders(email):
    """Return list of orders for a given user email."""
    orders = load_json(ORDERS_FILE)
    return [o for o in orders if o.get('user_email') == email]


def view_my_orders():
    if not CURRENT_USER:
        print("Tizimga kirilmagan. Iltimos avval tizimga kiring.")
        return
    orders = get_user_orders(CURRENT_USER.get('email'))
    if not orders:
        print("Siz hali hech narsa sotib olmadingiz.")
        return
    print(f"\n--- {CURRENT_USER.get('name')} ning Xarid Tarixi ---")
    for o in orders:
        print(f"Buyurtma #{o['id']} - Jami: {o['total']:.2f} - Sana: {o.get('created_at')}")
        for it in o.get('items', []):
            print(f"  - {it.get('name')} x {it.get('qty')}")


def add_to_cart(prod_id, qty):
    # validation
    if qty <= 0:
        print("Soni musbat butun son bo'lishi kerak.")
        return
    product = find_product(prod_id)
    if not product:
        print("Mahsulot topilmadi.")
        return
    if product.get("stock", 0) < qty:
        print(f"Yetarli stock yo'q. Mavjud: {product.get('stock')}")
        return
    # confirm
    if not ask_confirm(f"{product['name']} ni {qty} dona savatchaga qo'shishni tasdiqlaysizmi? (ha/no): "):
        print("Qo'shish bekor qilindi.")
        return
    cart = load_cart()
    # merge if exists
    for item in cart["items"]:
        if item["product_id"] == prod_id:
            item["qty"] += qty
            break
    else:
        cart["items"].append({
            "product_id": prod_id,
            "qty": qty,
            "unit_price": product["price"],
            "name": product["name"]
        })
    save_cart(cart)
    print("Mahsulot savatchaga qo'shildi.")


def view_cart():
    cart = load_cart()
    if not cart["items"]:
        print("Savatcha bo'sh.")
        return
    total = 0.0
    print("Savatcha:")
    for it in cart["items"]:
        line = it["unit_price"] * it["qty"]
        total += line
        print(f"- [{it['product_id']}] {it['name']} x {it['qty']} = {line:.2f}")
    print(f"Jami: {total:.2f}")


def clear_cart():
    if not load_cart()["items"]:
        print("Savatcha bo'sh.")
        return
    if ask_confirm("Savatchani tozalashni tasdiqlaysizmi? (ha/no): "):
        save_cart({"items": []})
        print("Savatcha tozalandi.")
    else:
        print("Amal bekor qilindi.")


def remove_from_cart(prod_id):
    cart = load_cart()
    target = next((it for it in cart["items"] if it["product_id"] == prod_id), None)
    if not target:
        print("Mahsulot savatchada topilmadi.")
        return
    if ask_confirm(f"{target['name']} ni savatchadan o'chirishni tasdiqlaysizmi? (ha/no): "):
        cart["items"] = [it for it in cart["items"] if it["product_id"] != prod_id]
        save_cart(cart)
        print("Mahsulot savatchadan o'chirildi.")
    else:
        print("Amal bekor qilindi.")


# Checkout (prototype)

def compute_membership_effects(total, membership_id, qty=None, shipping_method=None):
    """Return a dict describing membership effects on the given order total.
    Keys: membership (dict or None), discount (float), total_after_discount (float),
    points_earned (int), priority_support (bool), free_shipping (bool), special_discount (float)
    """
    result = {
        "membership": None,
        "discount": 0.0,
        "total_after_discount": total,
        "points_earned": 0,
        "priority_support": False,
        "free_shipping": False,
        "special_discount": 0.0
    }
    if not membership_id:
        return result
    memberships = show_memberships()
    mem = next((m for m in memberships if m["id"] == membership_id), None)
    if not mem:
        return result
    result["membership"] = mem
    # base discount
    base_discount = total * mem.get("discount_rate", 0.0)
    result["discount"] = base_discount
    # points
    points_mult = mem.get("points_multiplier", 1)
    result["points_earned"] = int(total * points_mult)
    # priority support
    result["priority_support"] = bool(mem.get("priority_support", False))
    # special business bulk pricing: if Business and qty provided and qty >= 10 give extra 10% off
    special = 0.0
    if mem.get("name", "").lower() == "business" and qty and qty >= 10:
        special = total * 0.10
        result["special_discount"] = special
        result["discount"] += special
    # total after discounts
    result["total_after_discount"] = max(total - result["discount"], 0.0)
    # free shipping: if membership has free_shipping_threshold and shipping_method is delivery
    threshold = mem.get("free_shipping_threshold")
    if shipping_method and shipping_method == "delivery" and threshold is not None:
        result["free_shipping"] = total >= float(threshold)
    return result


def apply_membership_discount(total, membership_id, qty=None, shipping_method=None):
    """Backwards-compatible wrapper: return (total_after, discount_amount)
    Accepts optional qty and shipping_method to support business bulk pricing and free-shipping checks."""
    eff = compute_membership_effects(total, membership_id, qty=qty, shipping_method=shipping_method)
    return eff["total_after_discount"], eff["discount"]


def apply_promo(total, code):
    if not code:
        return total, 0.0
    promos = get_promotions()
    now = datetime.now().date()
    for p in promos:
        if p["code"].lower() == code.lower():
            start = datetime.strptime(p["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(p["end_date"], "%Y-%m-%d").date()
            if start <= now <= end:
                if p["discount_type"] == "percent":
                    discount = total * (p["value"] / 100.0)
                else:
                    discount = p["value"]
                return max(total - discount, 0.0), discount
    print("Promo kod topilmadi yoki amal qilish muddati tugagan.")
    return total, 0.0


def checkout():
    cart = load_cart()
    if not cart["items"]:
        print("Savatcha bo'sh. Avval mahsulot qo'shing.")
        return
    subtotal = sum(it["unit_price"] * it["qty"] for it in cart["items"])
    print(f"Subtotal: {subtotal:.2f}")
    # membership (if user already bought a membership, ask whether to use it)
    membership_id = None
    if CURRENT_USER and isinstance(CURRENT_USER, dict) and CURRENT_USER.get('membership_id'):
        use_mem = input("Sizda a'zolik mavjud. Chegirmadan foydalanasizmi? (ha/no): ").strip().lower()
        if use_mem in ("ha", "yes", "y"):
            membership_id = CURRENT_USER.get('membership_id')
    else:
        mem_choice = input("A'zolik ID (yoksa ENTER): ").strip()
        membership_id = int(mem_choice) if mem_choice.isdigit() else None
        if membership_id:
            mems = show_memberships()
            if not any(m['id'] == membership_id for m in mems):
                print("Bunday a'zolik topilmadi. A'zolik e'tiborga olinmaydi.")
                membership_id = None
    qty_total = sum(it.get('qty', 0) for it in cart['items'])
    total_after_mem, mem_discount = apply_membership_discount(subtotal, membership_id, qty=qty_total)
    # display richer membership info
    mem_eff_preview = compute_membership_effects(subtotal, membership_id, qty=qty_total, shipping_method=None)
    print(f"A'zolik chegirmasi: {mem_discount:.2f} -> {total_after_mem:.2f}")
    if mem_eff_preview["points_earned"]:
        print(f"A'zolik ballari (kupon/ballar): {mem_eff_preview['points_earned']}")
    if mem_eff_preview["priority_support"]:
        print("Sizga ustuvor qo'llab-quvvatlash taqdim etiladi.")
    # promo
    promo_code = input("Promo kod (yoksa ENTER): ").strip()
    total_after_promo, promo_discount = apply_promo(total_after_mem, promo_code)
    print(f"Promo chegirma: {promo_discount:.2f} -> {total_after_promo:.2f}")
    # shipping
    while True:
        shipping_method = input("Yetkazib berish yoki pickup? (delivery/pickup): ").strip().lower()
        if shipping_method in ("delivery", "pickup"):
            break
        print("Iltimos 'delivery' yoki 'pickup' yozing.")
    shipping_fee = 0.0
    address = None
    if shipping_method == "delivery":
        while True:
            address = input("Yetkazib berish manzili (b->bekor qilish): ").strip()
            if not address:
                print("Manzil bo'sh bo'lishi mumkin emas.")
                continue
            if address.lower() in ("b", "back", "0"):
                print("Checkout bekor qilindi.")
                return
            break
        # recompute membership effects with shipping method to see if free shipping applies
        mem_eff = compute_membership_effects(subtotal, membership_id, qty=qty_total, shipping_method=shipping_method)
        if mem_eff["free_shipping"]:
            shipping_fee = 0.0
        else:
            shipping_fee = SHIPPING_FEE
    total = total_after_promo + shipping_fee
    print(f"Yakuniy to'lov: {total:.2f} (shipping: {shipping_fee:.2f})")
    confirm = input("Buyurtmani tasdiqlaysizmi? (ha/no): ").strip().lower()
    if confirm not in ("ha", "yes", "y"):
        print("Buyurtma bekor qilindi.")
        return
    # create order and update stocks
    orders = load_json(ORDERS_FILE)
    order = {
        "id": len(orders) + 1,
        "items": cart["items"],
        "subtotal": subtotal,
        "membership_discount": mem_discount,
        "promo_discount": promo_discount,
        "shipping_fee": shipping_fee,
        "total": total,
        "shipping_method": shipping_method,
        "address": address,
        "user_email": CURRENT_USER.get("email") if CURRENT_USER else None,
        "user_name": CURRENT_USER.get("name") if CURRENT_USER else None,
        "created_at": datetime.now().isoformat()
    }
    # decrement stock
    products = load_json(PRODUCTS_FILE)
    for it in cart["items"]:
        for p in products:
            if p["id"] == it["product_id"]:
                p["stock"] = max(0, p.get("stock", 0) - it["qty"])
    save_json(PRODUCTS_FILE, products)
    orders.append(order)
    save_json(ORDERS_FILE, orders)
    # record order under user if logged in
    if CURRENT_USER:
        users = load_users()
        u = next((x for x in users if x.get('email') == CURRENT_USER.get('email')), None)
        if u is not None:
            u.setdefault('orders', []).append(order['id'])
            save_users(users)
    clear_cart()
    print(f"Buyurtma #{order['id']} qabul qilindi. Jami: {total:.2f}")


def purchase_product_direct(prod_id, qty):
    product = find_product(prod_id)
    if not product:
        print("Mahsulot topilmadi.")
        return False
    if qty <= 0:
        print("Soni musbat butun son bo'lishi kerak.")
        return False
    if product.get("stock", 0) < qty:
        print(f"Yetarli stock yo'q. Mavjud: {product.get('stock')}")
        return False
    subtotal = product["price"] * qty
    print(f"Subtotal: {subtotal:.2f}")
    # membership (if user already bought a membership, ask whether to use it)
    membership_id = None
    if CURRENT_USER and isinstance(CURRENT_USER, dict) and CURRENT_USER.get('membership_id'):
        use_mem = input("Sizda a'zolik mavjud. Chegirmadan foydalanasizmi? (ha/no): ").strip().lower()
        if use_mem in ("ha", "yes", "y"):
            membership_id = CURRENT_USER.get('membership_id')
    else:
        mem_choice = input("A'zolik ID (yoksa ENTER): ").strip()
        membership_id = int(mem_choice) if mem_choice.isdigit() else None
        if membership_id:
            mems = show_memberships()
            if not any(m['id'] == membership_id for m in mems):
                print("Bunday a'zolik topilmadi. A'zolik e'tiborga olinmaydi.")
                membership_id = None
    total_after_mem, mem_discount = apply_membership_discount(subtotal, membership_id, qty=qty)
    mem_eff_preview = compute_membership_effects(subtotal, membership_id, qty=qty, shipping_method=None)
    print(f"A'zolik chegirmasi: {mem_discount:.2f} -> {total_after_mem:.2f}")
    if mem_eff_preview["points_earned"]:
        print(f"A'zolik ballari: {mem_eff_preview['points_earned']}")
    if mem_eff_preview["priority_support"]:
        print("Sizga ustuvor qo'llab-quvvatlash taqdim etiladi.")
    # promo
    promo_code = input("Promo kod (yoksa ENTER): ").strip()
    total_after_promo, promo_discount = apply_promo(total_after_mem, promo_code)
    print(f"Promo chegirma: {promo_discount:.2f} -> {total_after_promo:.2f}")
    # shipping
    while True:
        shipping_method = input("Yetkazib berish yoki pickup? (delivery/pickup): ").strip().lower()
        if shipping_method in ("delivery", "pickup"):
            break
        print("Iltimos 'delivery' yoki 'pickup' yozing.")
    shipping_fee = 0.0
    address = None
    if shipping_method == "delivery":
        while True:
            address = input("Yetkazib berish manzili (b->bekor qilish): ").strip()
            if not address:
                print("Manzil bo'sh bo'lishi mumkin emas.")
                continue
            if address.lower() in ("b", "back", "0"):
                print("Buyurtma bekor qilindi.")
                return False
            break
        # check membership free shipping for delivery
        mem_eff = compute_membership_effects(subtotal, membership_id, qty=qty, shipping_method=shipping_method)
        if mem_eff["free_shipping"]:
            shipping_fee = 0.0
        else:
            shipping_fee = SHIPPING_FEE
    total = total_after_promo + shipping_fee
    print(f"Yakuniy to'lov: {total:.2f} (shipping: {shipping_fee:.2f})")
    if not ask_confirm("Buyurtmani tasdiqlaysizmi? (ha/no): "):
        print("Buyurtma bekor qilindi.")
        return False
    orders = load_json(ORDERS_FILE)
    order = {
        "id": len(orders) + 1,
        "items": [{
            "product_id": prod_id,
            "qty": qty,
            "unit_price": product["price"],
            "name": product["name"]
        }],
        "subtotal": subtotal,
        "membership_discount": mem_discount,
        "promo_discount": promo_discount,
        "shipping_fee": shipping_fee,
        "total": total,
        "shipping_method": shipping_method,
        "address": address,
        "user_email": CURRENT_USER.get("email") if CURRENT_USER else None,
        "user_name": CURRENT_USER.get("name") if CURRENT_USER else None,
        "created_at": datetime.now().isoformat()
    }
    products = load_json(PRODUCTS_FILE)
    for p in products:
        if p["id"] == prod_id:
            p["stock"] = max(0, p.get("stock", 0) - qty)
    save_json(PRODUCTS_FILE, products)
    orders.append(order)
    save_json(ORDERS_FILE, orders)
    # record order under user if logged in
    if CURRENT_USER:
        users = load_users()
        u = next((x for x in users if x.get('email') == CURRENT_USER.get('email')), None)
        if u is not None:
            u.setdefault('orders', []).append(order['id'])
            save_users(users)
    print(f"Buyurtma #{order['id']} qabul qilindi. Jami: {total:.2f}")
    return True


def purchase_membership(membership_id):
    """Allow the current user to purchase a membership package."""
    global CURRENT_USER
    if not CURRENT_USER:
        print("Iltimos avval tizimga kiring.")
        return False
    mems = show_memberships()
    mem = next((m for m in mems if m["id"] == membership_id), None)
    if not mem:
        print("Bunday a'zolik topilmadi.")
        return False
    price = float(mem.get("price", 0.0))
    print(f"Paket: {mem['name']} - Narx: {price:.2f}")
    if not ask_confirm("Sotib olishni tasdiqlaysizmi? (ha/no): "):
        print("Sotib olish bekor qilindi.")
        return False
    orders = load_json(ORDERS_FILE)
    order = {
        "id": len(orders) + 1,
        "items": [{
            "membership_id": membership_id,
            "qty": 1,
            "unit_price": price,
            "name": f"Membership: {mem['name']}"
        }],
        "subtotal": price,
        "membership_discount": 0.0,
        "promo_discount": 0.0,
        "shipping_fee": 0.0,
        "total": price,
        "shipping_method": "membership",
        "address": None,
        "user_email": CURRENT_USER.get("email") if CURRENT_USER else None,
        "user_name": CURRENT_USER.get("name") if CURRENT_USER else None,
        "created_at": datetime.now().isoformat()
    }
    orders.append(order)
    save_json(ORDERS_FILE, orders)
    # mark membership on user record (persist and in-memory)
    users = load_users()
    u = next((x for x in users if x.get('email') == CURRENT_USER.get('email')), None)
    if u is not None:
        u['membership_id'] = membership_id
        save_users(users)
        # update in-memory user
        CURRENT_USER['membership_id'] = membership_id
    print("A'zolik muvaffaqiyatli sotib olindi.")
    return True


# Support

def purchase_from_cart(prod_id):
    """Purchase a product from the cart by its product id. Returns True on success."""
    cart = load_cart()
    item = next((it for it in cart["items"] if it["product_id"] == prod_id), None)
    if not item:
        print("Mahsulot savatchada topilmadi.")
        return False
    qty = item["qty"]
    ok = purchase_product_direct(prod_id, qty)
    if ok:
        cart["items"] = [it for it in cart["items"] if it["product_id"] != prod_id]
        save_cart(cart)
        print("Mahsulot savatchadan sotib olindi va savatchadan o'chirildi.")
        return True
    else:
        print("Sotib olish bekor qilindi yoki muvaffaqiyatsiz tugadi.")
        return False


# Support

def send_support_message():
    while True:
        name = input("Ismingiz (b->orqaga): ").strip()
        if name.lower() in ("b", "back", "0") or not name:
            print("Bekor qilindi.")
            return
        email = input("Email: ").strip()
        if not email:
            print("Email bo'sh bo'lishi mumkin emas.")
            continue
        subject = input("Mavzu: ").strip()
        message = input("Xabar: ").strip()
        if not message:
            print("Xabar bo'sh bo'lishi mumkin emas.")
            continue
        if not ask_confirm("Xabarni yuborasizmi? (ha/no): "):
            print("Bekor qilindi.")
            return
        msgs = load_json(SUPPORT_FILE)
        msgs.append({
            "id": len(msgs) + 1,
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "status": "new",
            "created_at": datetime.now().isoformat()
        })
        save_json(SUPPORT_FILE, msgs)
        print("Xabaringiz qabul qilindi. Tez orada javob beramiz.")
        return


# CLI

def print_main():
    print("\n=== Tech House===")
    if CURRENT_USER:
        role = " (admin)" if CURRENT_USER.get("is_admin") else ""
        print(f"Logged in as: {CURRENT_USER.get('name')} <{CURRENT_USER.get('email')}>{role}")
    print("1. Toifalarni ko'rish")
    print("2. Mahsulotlarni ko'rish (barcha)")
    print("3. Toifaga ko'ra mahsulotlar")
    print("4. Mahsulot qidirish")
    print("5. Mahsulot tafsiloti")
    print("6. A'zolik paketlari")
    print("7. Savatchaga qo'shish")
    print("8. Savatchani ko'rish")
    print("9. Buyurtma berish (checkout)")
    print("10. Qo'llab‑quvvatlashga xabar yuborish")
    print("11. Mening xaridlarim")
    print("0. Chiqish")
    print("h. Yordam / Help")


def print_help():
    print("\n--- Yordam / Help ---")
    print("Qisqacha buyruqlar:")
    print("- 'add <id> <qty>' yoki 'a <id> <qty>' yoki '1' — mahsulotni savatchaga qo'shish")
    print("- 'buy <qty>' yoki 's <qty>' yoki '2' — mahsulotni birlamchi sotib olish (quick)")
    print("- 'v <id>' yoki 'view <id>' — mahsulot tafsilotini ko'rish")
    print("- 'remove <id>' — savatchadan o'chirish")
    print("- 'clear' — savatchani tozalash")
    print("- 'checkout' — xaridni yakunlash")
    print("- 'h' yoki 'help' — bu yordam ekranini ko'rsatish")
    print("\nLogin:\n- Dastur ishga tushganda ism, pochta va parol so'raladi. Agar pochta mavjud bo'lsa teskari parol bilan tizimga kiriladi; aks holda hisob yaratiladi.")
    print("- Admin uchun: email = actamovyusuf007@gmail.com, parol = luxnendo@890")
    print("- Tizimdan chiqish uchun menyuda 'logout' deb yozing.")
    print("---")


def main():
    # ensure data dir exists
    os.makedirs(DATA_DIR, exist_ok=True)
    # ensure cart exists
    if not os.path.exists(CART_FILE):
        save_json(CART_FILE, {"items": []})
    # ensure users file exists and admin is present
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, [])
    ensure_admin_user()
    # ask user to login before showing main menu
    login_prompt()
    while True:
        print_main()
        cmd = input("Tanlov (yoki 'logout' qayta kirish uchun): ").strip()
        if cmd.lower() == 'logout':
            print("Siz tizimdan chiqdingiz. Yana kirish uchun ma'lumot kiriting.")
            login_prompt()
            continue
        # 1) Categories submenu
        if cmd == "1":
            while True:
                cats = list_categories()
                for c in cats:
                    print(f"{c['id']}. {c['name']}")
                sub = input("Toifa ID (id->ko'rish, b->orqaga): ").strip()
                if sub.lower() in ("b", "back", "0") or not sub:
                    break
                if sub.isdigit():
                    
                    cid = int(sub)
                    while True:
                        prods = list_products(cid)
                        if not prods:
                            print("Bu toifada mahsulot yo'q.")
                        else:
                            for p in prods:
                                print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                        act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                        if act.lower() in ("b", "back", "0") or not act:
                            break
                        parts = act.split()
                        normalize_cmd_parts(parts)
                        if parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                            pid = int(parts[1])
                            prod = find_product(pid)
                            if not prod:
                                print("Mahsulot topilmadi.")
                            else:
                                print(json.dumps(prod, ensure_ascii=False, indent=2))
                                choice = input("[add <qty> | buy <qty> | b]: ").strip()
                                cparts = choice.split()
                                normalize_cmd_parts(cparts)
                                if not cparts:
                                    continue
                                if cparts[0].lower() == 'a':
                                    if len(cparts) >= 2 and cparts[1].isdigit():
                                        add_to_cart(pid, int(cparts[1]))
                                    else:
                                        qty = input("Soni: ").strip()
                                        if qty.isdigit():
                                            add_to_cart(pid, int(qty))
                                        else:
                                            print("Noto'g'ri son. Qo'shish bekor qilindi.")
                                elif cparts[0].lower() in ('s', 'buy', 'sotib'):
                                    if len(cparts) >= 2 and cparts[1].isdigit():
                                        purchase_product_direct(pid, int(cparts[1]))
                                    else:
                                        qty = input("Soni: ").strip()
                                        if qty.isdigit():
                                            purchase_product_direct(pid, int(qty))
                                        else:
                                            print("Noto'g'ri son. Sotib olish bekor qilindi.")
                                elif cparts[0].lower() in ('b', 'back', '0'):
                                    continue
                                else:
                                    print("Noto'g'ri tanlov.")
                        elif parts[0].lower() in ('a','add'):
                            # support 'add <id>' or 'add    <id>' or 'add' -> prompt for missing info
                            if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                                add_to_cart(int(parts[1]), int(parts[2]))
                            elif len(parts) >= 2 and parts[1].isdigit():
                                qty = input("Soni: ").strip()
                                if qty.isdigit():
                                    add_to_cart(int(parts[1]), int(qty))
                                else:
                                    print("Noto'g'ri son. Qo'shish bekor qilindi.")
                            else:
                                pid = input("Mahsulot ID: ").strip()
                                if not pid.isdigit():
                                    print("Noto'g'ri ID. Bekor qilindi.")
                                else:
                                    qty = input("Soni: ").strip()
                                    if qty.isdigit():
                                        add_to_cart(int(pid), int(qty))
                                    else:
                                        print("Noto'g'ri son. Qo'shish bekor qilindi.")
                        else:
                            print("Noto'g'ri tanlov.")
        # 2) All products 
        elif cmd == "2":
            while True:
                for p in list_products():
                    print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                if act.lower() in ("b", "back", "0") or not act:
                    break
                parts = act.split()
                normalize_cmd_parts(parts)
                if len(parts) == 1 and parts[0].isdigit():
                    pid = int(parts[0])
                    prod = find_product(pid)
                    if not prod:
                        print("Mahsulot topilmadi.")
                        continue
                    # show product details first
                    print(json.dumps(prod, ensure_ascii=False, indent=2))
                    choice = input("[1:add | 2:buy | b]: ").strip()
                    cparts = choice.split()
                    normalize_cmd_parts(cparts)
                    if not cparts:
                        continue
                    token = cparts[0].lower()
                    if token == 'a' or token == '1':
                        if len(cparts) >= 2 and cparts[1].isdigit():
                            add_to_cart(pid, int(cparts[1]))
                        else:
                            qty = input("Soni: ").strip()
                            if qty.isdigit():
                                add_to_cart(pid, int(qty))
                            else:
                                print("Noto'g'ri son. Qo'shish bekor qilindi.")
                    elif token in ('s', 'buy', 'sotib') or token == '2':
                        if len(cparts) >= 2 and cparts[1].isdigit():
                            purchase_product_direct(pid, int(cparts[1]))
                        else:
                            qty = input("Soni: ").strip()
                            if qty.isdigit():
                                purchase_product_direct(pid, int(qty))
                            else:
                                print("Noto'g'ri son. Sotib olish bekor qilindi.")
                    elif token in ('b', 'back', '0'):
                        continue
                    else:
                        print("Noto'g'ri tanlov.")
                elif parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                    p = find_product(int(parts[1]))
                    if p:
                        print(json.dumps(p, ensure_ascii=False, indent=2))
                    else:
                        print("Mahsulot topilmadi.")
                elif parts[0].lower() == 'a' and len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                    add_to_cart(int(parts[1]), int(parts[2]))
                else:
                    print("Noto'g'ri tanlov.")
        # 3) Products by category
        elif cmd == "3":
            while True:
                cid = input("Toifa ID (b->orqaga): ").strip()
                if cid.lower() in ("b", "back", "0") or not cid:
                    break
                if cid.isdigit():
                    cid = int(cid)
                    while True:
                        prods = list_products(cid)
                        if not prods:
                            print("Bu toifada mahsulot yo'q.")
                        else:
                            for p in prods:
                                print(f"{p['id']}. {p['name']} - {p['price']:.2f} (stock: {p.get('stock')})")
                        act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                        if act.lower() in ("b", "back", "0") or not act:
                            break
                        parts = act.split()
                        normalize_cmd_parts(parts)
                        # if user types only a product id, show quick actions
                        if len(parts) == 1 and parts[0].isdigit():
                            pid = int(parts[0])
                            prod = find_product(pid)
                            if not prod:
                                print("Mahsulot topilmadi.")
                                continue
                            # show product details first
                            print(json.dumps(prod, ensure_ascii=False, indent=2))
                            choice = input("[add <qty> qo'shish | buy <qty> sotib olish | v ko'rish | b orqaga]: ").strip()
                            cparts = choice.split()
                            normalize_cmd_parts(cparts)
                            if not cparts:
                                continue
                            if cparts[0].lower() == 'v':
                                print(json.dumps(prod, ensure_ascii=False, indent=2))
                            elif cparts[0].lower() in ('a', 'add'):
                                if len(cparts) >= 2 and cparts[1].isdigit():
                                    add_to_cart(pid, int(cparts[1]))
                                else:
                                    qty = input("Soni: ").strip()
                                    if qty.isdigit():
                                        add_to_cart(pid, int(qty))
                                    else:
                                        print("Noto'g'ri son. Qo'shish bekor qilindi.")
                            elif cparts[0].lower() in ('s', 'buy', 'sotib'):
                                if len(cparts) >= 2 and cparts[1].isdigit():
                                    purchase_product_direct(pid, int(cparts[1]))
                                else:
                                    qty = input("Soni: ").strip()
                                    if qty.isdigit():
                                        purchase_product_direct(pid, int(qty))
                                    else:
                                        print("Noto'g'ri son. Sotib olish bekor qilindi.")
                            elif cparts[0].lower() in ('b', 'back', '0'):
                                continue
                            else:
                                print("Noto'g'ri tanlov.")
                        elif parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                            p = find_product(int(parts[1]))
                            if p:
                                print(json.dumps(p, ensure_ascii=False, indent=2))
                            else:
                                print("Mahsulot topilmadi.")
                        elif parts[0].lower() in ('a','add') and len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                            add_to_cart(int(parts[1]), int(parts[2]))
                        else:
                            print("Noto'g'ri tanlov. Mahsulotni tanlash uchun ID raqamini yozing yoki 'add <id> <qty>' yoki 'v <id>' deb yozing.")
        # 4) Search
        elif cmd == "4":
            while True:
                q = input("Qidiruv so'zi (b->orqaga): ").strip()
                if q.lower() in ("b", "back", "0") or not q:
                    break
                results = search_products(q)
                for p in results:
                    print(f"{p['id']}. {p['name']} - {p['price']:.2f}")
                act = input("[v <id> ko'rish | add <id> <qty> qo'shish | b orqaga]: ").strip()
                if act.lower() in ("b", "back", "0") or not act:
                    continue
                parts = act.split()
                normalize_cmd_parts(parts)
                if len(parts) == 1 and parts[0].isdigit():
                    pid = int(parts[0])
                    prod = find_product(pid)
                    if not prod:
                        print("Mahsulot topilmadi.")
                        continue
                    # show product details first
                    print(json.dumps(prod, ensure_ascii=False, indent=2))
                    choice = input("[1:add | 2:buy | b]: ").strip()
                    cparts = choice.split()
                    normalize_cmd_parts(cparts)
                    if not cparts:
                        continue
                    token = cparts[0].lower()
                    if token == 'a' or token == '1':
                        if len(cparts) >= 2 and cparts[1].isdigit():
                            add_to_cart(pid, int(cparts[1]))
                        else:
                            qty = input("Soni: ").strip()
                            if qty.isdigit():
                                add_to_cart(pid, int(qty))
                            else:
                                print("Noto'g'ri son. Qo'shish bekor qilindi.")
                    elif token in ('s', 'buy', 'sotib') or token == '2':
                        if len(cparts) >= 2 and cparts[1].isdigit():
                            purchase_product_direct(pid, int(cparts[1]))
                        else:
                            qty = input("Soni: ").strip()
                            if qty.isdigit():
                                purchase_product_direct(pid, int(qty))
                            else:
                                print("Noto'g'ri son. Sotib olish bekor qilindi.")
                    elif token in ('b', 'back', '0'):
                        continue
                    else:
                        print("Noto'g'ri tanlov.")
                elif parts[0].lower() == 'v' and len(parts) >= 2 and parts[1].isdigit():
                    p = find_product(int(parts[1]))
                    if p:
                        print(json.dumps(p, ensure_ascii=False, indent=2))
                    else:
                        print("Mahsulot topilmadi.")
                elif parts[0].lower() == 'a' and len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                    add_to_cart(int(parts[1]), int(parts[2]))
                else:
                    print("Noto'g'ri tanlov.")
        # 5) Product detail 
        elif cmd == "5":
            while True:
                pid = input("Mahsulot ID (b->orqaga): ").strip()
                if pid.lower() in ("b", "back", "0") or not pid:
                    break
                if pid.isdigit():
                    p = find_product(int(pid))
                    if p:
                        print(json.dumps(p, ensure_ascii=False, indent=2))
                        act = input("[add <qty> qo'shish | buy <qty> sotib olish | b orqaga]: ").strip()
                        if act.lower() in ("b", "back", "0") or not act:
                            continue
                        parts = act.split()
                        normalize_cmd_parts(parts)
                        token = parts[0].lower()
                        if token in ('a', 'add') or token == '1':
                            if len(parts) >= 2 and parts[1].isdigit():
                                add_to_cart(p['id'], int(parts[1]))
                            else:
                                qty = input("Soni: ").strip()
                                if qty.isdigit():
                                    add_to_cart(p['id'], int(qty))
                                else:
                                    print("Noto'g'ri son. Qo'shish bekor qilindi.")
                        elif token in ('buy', 's', 'sotib') or token == '2':
                            if len(parts) >= 2 and parts[1].isdigit():
                                purchase_product_direct(p['id'], int(parts[1]))
                            else:
                                qty = input("Soni: ").strip()
                                if qty.isdigit():
                                    purchase_product_direct(p['id'], int(qty))
                                else:
                                    print("Noto'g'ri son. Sotib olish bekor qilindi.")
                        else:
                            print("Noto'g'ri tanlov.")
                    else:
                        print("Mahsulot topilmadi.")
        # 6) Memberships
        elif cmd == "6":
            while True:
                print("\n--- A'zolik paketlari ---")
                for m in show_memberships():
                    thr = m.get('free_shipping_threshold')
                    thr_text = f"bepul yetkazib berish >= {thr:.2f}" if thr is not None else "bepul yetkazib berish: yo'q"
                    print(f"{m['id']}. {m['name']} - chegirma: {m.get('discount_rate',0)*100:.0f}% | ballar koeff: {m.get('points_multiplier')} | ustuvor: {m.get('priority_support')} | {thr_text} | narx: {m.get('price',0):.2f}")
                sub = input("Paket ID sotib olish uchun kiriting yoki b->orqaga: ").strip()
                if sub.lower() in ('b','back','0','') or not sub:
                    break
                if sub.isdigit():
                    mid = int(sub)
                    if purchase_membership(mid):
                        users = load_users()
                        u = next((x for x in users if x.get('email') == CURRENT_USER.get('email')), None)
                        if u is not None and isinstance(CURRENT_USER, dict):
                            CURRENT_USER.clear()
                            CURRENT_USER.update(u)
                        print("A'zolik sotib olindi. Asosiy menyuga qaytilmoqda.")
                        break
                else:
                    print("Noto'g'ri tanlov.")
        # 7) Add to cart 
        elif cmd == "7":
            while True:
                pid = input("Mahsulot ID (b->orqaga): ").strip()
                if pid.lower() in ("b", "back", "0") or not pid:
                    break
                qty = input("Soni: ").strip()
                if pid.isdigit() and qty.isdigit():
                    add_to_cart(int(pid), int(qty))
                else:
                    print("Noto'g'ri kirish.")
        # 8) Cart menu
        elif cmd == "8":
            while True:
                view_cart()
                act = input("[remove <product_id> | buy <product_id> | b orqaga]: ").strip()
                if act.lower() in ("b", "back", "0") or not act:
                    break
                parts = act.split()
                if parts[0].lower() == 'remove' and len(parts) >= 2 and parts[1].isdigit():
                    remove_from_cart(int(parts[1]))
                elif parts[0].lower() in ('buy', 's', 'sotib') and len(parts) >= 2 and parts[1].isdigit():
                    pid = int(parts[1])
                    purchase_from_cart(pid)
                else:
                    print("Noto'g'ri tanlov. Faqat 'remove <id>' yoki 'buy <id>' qabul qilinadi.")
        # 9) Checkout 
        elif cmd == "9":
            while True:
                checkout()
                again = input("Yana buyurtma berasizmi? (ha->yana / b->menyuga qaytish): ").strip().lower()
                if again in ("b", "back", "0", "no"):
                    break
        # 10) Support
        elif cmd == "10":
            while True:
                sub = input("[s->xabar yuborish | b->orqaga]: ").strip().lower()
                if sub in ("b", "back", "0") or not sub:
                    break
                if sub == 's':
                    send_support_message()
                else:
                    print("Noto'g'ri tanlov.")
        # 11) View my orders
        elif cmd == "11":
            view_my_orders()
        elif cmd.lower() in ('h', 'help', '?'):
            print_help()
            continue
        elif cmd == "0":
            print("Xayr!")
            break
        else:
            print("Noto'g'ri tanlov. Iltimos menyudan amallarni tanlang yoki yordam uchun dokumentatsiyaga murojaat qiling.")


if __name__ == '__main__':
    try:
        CLI().main()
    except KeyboardInterrupt:
        pass
    except (SystemExit, Exception):
        print("\nDastur yopildi.")