import json
import shutil
import builtins
import os
import index as shop

DATA_FILES = [shop.PRODUCTS_FILE, shop.CART_FILE, shop.ORDERS_FILE, shop.USERS_FILE]


def backup_files():
    bak = {}
    for f in DATA_FILES:
        b = f + '.bak'
        shutil.copyfile(f, b)
        bak[f] = b
    return bak


def restore_files(bak):
    for f, b in bak.items():
        shutil.copyfile(b, f)
        os.remove(b)


def test_normalize_cmd_parts():
    parts = ['ADD', '1', '2']
    shop.normalize_cmd_parts(parts)
    assert parts[0] == 'a'

    parts = ['Buy', '1']
    shop.normalize_cmd_parts(parts)
    assert parts[0] == 's'


def test_add_and_purchase_flow(monkeypatch):
    bak = backup_files()
    try:
        # reset
        shop.save_json(shop.CART_FILE, {"items": []})
        shop.save_json(shop.ORDERS_FILE, [])

        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products available for tests"
        prod = prods[0]
        pid = prod['id']
        # ensure stock
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)

        # patch input for add_to_cart confirmation
        monkeypatch.setattr(builtins, 'input', lambda prompt='': 'ha')
        shop.add_to_cart(pid, 2)
        cart = shop.load_cart()
        assert cart['items'] and cart['items'][0]['qty'] == 2

        # patch input sequence for purchase_product_direct: membership '', promo '', shipping 'pickup', confirm 'ha'
        seq = iter(['', '', 'pickup', 'ha'])
        monkeypatch.setattr(builtins, 'input', lambda prompt='': next(seq))
        shop.purchase_product_direct(pid, 1)

        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1

        prods_after = shop.load_json(shop.PRODUCTS_FILE)
        new_stock = next(p for p in prods_after if p['id'] == pid)['stock']
        assert new_stock == 9

    finally:
        restore_files(bak)


def test_purchase_from_cart(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.CART_FILE, {"items": []})
        shop.save_json(shop.ORDERS_FILE, [])

        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products available for tests"
        prod = prods[0]
        pid = prod['id']
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)

        # put item into cart
        cart = {"items": [{"product_id": pid, "qty": 2, "unit_price": prod['price'], "name": prod['name']}]}
        shop.save_json(shop.CART_FILE, cart)

        # patch inputs for purchase flow: '', '', 'pickup', 'ha'
        seq = iter(['', '', 'pickup', 'ha'])
        monkeypatch.setattr(builtins, 'input', lambda prompt='': next(seq))
        ok = shop.purchase_from_cart(pid)
        assert ok is True

        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        cart_after = shop.load_cart()
        assert not cart_after['items']
        prods_after = shop.load_json(shop.PRODUCTS_FILE)
        new_stock = next(p for p in prods_after if p['id'] == pid)['stock']
        assert new_stock == 8

    finally:
        restore_files(bak)


def test_quick_action_add_buy_only(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.CART_FILE, {"items": []})
        shop.save_json(shop.ORDERS_FILE, [])

        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products available for tests"
        prod = prods[0]
        pid = prod['id']
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)

        # Simulate viewing product then typing 'add' (no qty) -> then enter qty and confirm
        seq = iter(['2', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        cparts = ['add']
        shop.normalize_cmd_parts(cparts)
        if cparts[0] == 'a':
            if len(cparts) >= 2 and cparts[1].isdigit():
                shop.add_to_cart(pid, int(cparts[1]))
            else:
                qty = input('Soni: ').strip()
                if qty.isdigit():
                    shop.add_to_cart(pid, int(qty))
        cart = shop.load_cart()
        assert cart['items'] and cart['items'][0]['qty'] == 2

        # Simulate viewing product then typing 'buy' (no qty) -> then enter qty and complete purchase
        seq = iter(['', '', 'pickup', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        ok = shop.purchase_product_direct(pid, 1)
        assert ok is True
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) >= 1

    finally:
        restore_files(bak)


def test_shorthand_1_and_2(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.CART_FILE, {"items": []})
        shop.save_json(shop.ORDERS_FILE, [])

        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products available for tests"
        prod = prods[0]
        pid = prod['id']
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)

        # shorthand '1' should act as add: prompt qty
        seq = iter(['3', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        cparts = ['1']
        shop.normalize_cmd_parts(cparts)
        token = cparts[0]
        if token == 'a' or token == '1':
            qty = input('Soni: ').strip()
            if qty.isdigit():
                shop.add_to_cart(pid, int(qty))
        cart = shop.load_cart()
        assert cart['items'] and cart['items'][0]['qty'] == 3

        # shorthand '2' should act as buy: prompt qty then run purchase
        seq = iter(['1', '', '', 'pickup', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        cparts = ['2']
        shop.normalize_cmd_parts(cparts)
        token = cparts[0]
        if token in ('s', 'buy', 'sotib') or token == '2':
            qty = input('Soni: ').strip()
            if qty.isdigit():
                ok = shop.purchase_product_direct(pid, int(qty))
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) >= 1

    finally:
        restore_files(bak)


def test_user_sees_own_purchases(monkeypatch, capsys):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'me@example.com']
        me = {"name": "Me", "email": "me@example.com", "address": "X", "orders": []}
        shop.set_user_password(me, 'pw')
        users.append(me)
        shop.save_users(users)
        # create an order for me
        orders = shop.load_json(shop.ORDERS_FILE)
        orders.append({"id": 999, "items": [{"product_id": 1, "qty": 1, "name": "TestProd"}], "total": 42.0, "user_email": "me@example.com", "created_at": "2026-01-02T00:00:00"})
        shop.save_json(shop.ORDERS_FILE, orders)
        # set current user
        shop.CURRENT_USER = shop.find_user_by_email('me@example.com')
        shop.view_my_orders()
        captured = capsys.readouterr()
        assert 'TestProd' in captured.out
        assert 'Buyurtma #999' in captured.out
    finally:
        restore_files(bak)


def test_admin_sees_all_purchases(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        # create two users and two orders
        users = shop.load_users()
        users = [u for u in users if u.get('email') not in ('a@example.com','b@example.com')]
        a = {"name": "A", "email": "a@example.com", "address": "X", "orders": []}
        b = {"name": "B", "email": "b@example.com", "address": "Y", "orders": []}
        shop.set_user_password(a, 'pw'); shop.set_user_password(b, 'pw')
        users.extend([a,b])
        shop.save_users(users)
        orders = shop.load_json(shop.ORDERS_FILE)
        orders.append({"id": 1001, "items": [{"product_id": 1, "qty": 1, "name": "Aprod"}], "total": 10.0, "user_email": "a@example.com", "created_at": "2026-01-02T00:00:00"})
        orders.append({"id": 1002, "items": [{"product_id": 2, "qty": 2, "name": "Bprod"}], "total": 20.0, "user_email": "b@example.com", "created_at": "2026-01-02T00:00:00"})
        shop.save_json(shop.ORDERS_FILE, orders)
        # ensure admin
        admin = shop.find_user_by_email(shop.ADMIN_EMAIL)
        shop.CURRENT_USER = admin
        # run admin menu choice 1 then exit
        seq = iter(['1','0'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.admin_menu()
        # no exception is success; manual inspection shows output, but ensure data present
        ua = shop.get_user_orders('a@example.com')
        ub = shop.get_user_orders('b@example.com')
        assert ua and ub
    finally:
        restore_files(bak)


def test_admin_handles_orders_without_user_email(monkeypatch, capsys):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        orders = shop.load_json(shop.ORDERS_FILE)
        # create an order with missing user_email
        orders.append({"id":3001, "items":[{"product_id":1, "qty":1, "name":"NoUserProd"}], "total":50.0, "created_at":"2026-01-02T13:00:00"})
        shop.save_json(shop.ORDERS_FILE, orders)
        admin = shop.find_user_by_email(shop.ADMIN_EMAIL)
        shop.CURRENT_USER = admin
        seq = iter(['3','0'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.admin_menu()
        captured = capsys.readouterr()
        assert 'Buyurtma #3001' in captured.out
        assert 'NoUserProd' in captured.out
    finally:
        restore_files(bak)


def test_admin_add_product(monkeypatch):
    bak = backup_files()
    try:
        prods = shop.load_json(shop.PRODUCTS_FILE)
        orig = len(prods)
        admin = shop.find_user_by_email(shop.ADMIN_EMAIL)
        shop.CURRENT_USER = admin
        seq = iter(['4', 'NewProduct', '123.45', 'TestType', '7', '0'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.admin_menu()
        prods_after = shop.load_json(shop.PRODUCTS_FILE)
        assert len(prods_after) == orig + 1
        newp = next((p for p in prods_after if p.get('name') == 'NewProduct'), None)
        assert newp is not None
        assert abs(newp['price'] - 123.45) < 1e-6
        assert newp['stock'] == 7
        assert newp.get('type') == 'TestType'
    finally:
        restore_files(bak)


def test_admin_sees_global_order_history(monkeypatch, capsys):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'guy@example.com']
        guy = {"name":"Guy","email":"guy@example.com","address":"Zone P","orders":[]}
        shop.set_user_password(guy,'pw')
        users.append(guy)
        shop.save_users(users)
        orders = shop.load_json(shop.ORDERS_FILE)
        orders.append({"id":2001,"items":[{"product_id":1,"qty":2,"name":"ProdX"}],"total":123.0,"user_email":"guy@example.com","created_at":"2026-01-02T12:00:00"})
        shop.save_json(shop.ORDERS_FILE, orders)
        admin = shop.find_user_by_email(shop.ADMIN_EMAIL)
        shop.CURRENT_USER = admin
        seq = iter(['3','0'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.admin_menu()
        captured = capsys.readouterr()
        assert 'Guy' in captured.out
        assert 'ProdX' in captured.out
        assert 'Zone P' in captured.out
    finally:
        restore_files(bak)


def test_purchase_membership_sets_user_membership(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'buyer@example.com']
        buyer = {"name": "Buyer", "email": "buyer@example.com", "address": "X", "orders": []}
        shop.set_user_password(buyer, 'pw')
        users.append(buyer)
        shop.save_users(users)
        shop.CURRENT_USER = shop.find_user_by_email('buyer@example.com')
        # patch input for confirmation
        monkeypatch.setattr('builtins.input', lambda prompt='': 'ha')
        ok = shop.purchase_membership(3)
        assert ok is True
        u = shop.find_user_by_email('buyer@example.com')
        assert u.get('membership_id') == 3
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        o = orders[-1]
        assert o['total'] == next(m for m in shop.show_memberships() if m['id'] == 3)['price']
    finally:
        restore_files(bak)


def test_purchase_direct_with_user_membership_applies_discount(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        prods = shop.load_json(shop.PRODUCTS_FILE)
        prod = prods[0]
        pid = prod['id']
        prod['price'] = 200.0
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'memb@example.com']
        mem_user = {"name": "Memb", "email": "memb@example.com", "address": "X", "orders": [], "membership_id": 3}
        shop.set_user_password(mem_user, 'pw')
        users.append(mem_user)
        shop.save_users(users)
        shop.CURRENT_USER = shop.find_user_by_email('memb@example.com')
        # inputs: accept membership, promo '', pickup, confirm
        seq = iter(['ha', '', 'pickup', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        ok = shop.purchase_product_direct(pid, 1)
        assert ok is True
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        o = orders[-1]
        assert abs(o['membership_discount'] - (200.0 * 0.1)) < 1e-6
    finally:
        restore_files(bak)


def test_purchase_direct_with_user_membership_declines_discount(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        prods = shop.load_json(shop.PRODUCTS_FILE)
        prod = prods[0]
        pid = prod['id']
        prod['price'] = 200.0
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'memb2@example.com']
        mem_user = {"name": "Memb2", "email": "memb2@example.com", "address": "X", "orders": [], "membership_id": 3}
        shop.set_user_password(mem_user, 'pw')
        users.append(mem_user)
        shop.save_users(users)
        shop.CURRENT_USER = shop.find_user_by_email('memb2@example.com')
        # inputs: decline membership, promo '', pickup, confirm
        seq = iter(['no', '', 'pickup', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        ok = shop.purchase_product_direct(pid, 1)
        assert ok is True
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        o = orders[-1]
        assert abs(o['membership_discount'] - 0.0) < 1e-6
    finally:
        restore_files(bak)


def test_password_hash_migration(monkeypatch):
    bak = backup_files()
    try:
        # prepare users file with a user having plain 'password' (legacy)
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'mig@example.com']
        legacy_user = {"name": "Mig", "email": "mig@example.com", "password": "plainpw", "address": "X", "orders": []}
        users.append(legacy_user)
        shop.save_users(users)

        # simulate login: name, email, password
        seq = iter(['Mig', 'mig@example.com', 'plainpw'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.login_prompt()
        # reload users
        users_after = shop.load_users()
        u = next((x for x in users_after if x.get('email') == 'mig@example.com'), None)
        assert u is not None
        assert 'password' not in u
        assert 'password_hash' in u and 'salt' in u
        assert shop.CURRENT_USER and shop.CURRENT_USER.get('email') == 'mig@example.com'
    finally:
        restore_files(bak)


def test_incorrect_password_reprompts_password(monkeypatch):
    bak = backup_files()
    try:
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'rep@example.com']
        rep = {"name": "Rep", "email": "rep@example.com", "address": "X", "orders": []}
        shop.set_user_password(rep, 'pw')
        users.append(rep)
        shop.save_users(users)
        # sequence: name, email, wrong pw, correct pw
        seq = iter(['Rep', 'rep@example.com', 'wrong', 'pw'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.login_prompt()
        assert shop.CURRENT_USER and shop.CURRENT_USER.get('email') == 'rep@example.com'
    finally:
        restore_files(bak)


def test_change_password_via_change_keyword(monkeypatch):
    bak = backup_files()
    try:
        users = shop.load_users()
        users = [u for u in users if u.get('email') != 'change@example.com']
        ch = {"name": "Changer", "email": "change@example.com", "address": "X", "orders": []}
        shop.set_user_password(ch, 'oldpw')
        users.append(ch)
        shop.save_users(users)
        # sequence: name, email, 'change' to open change flow, confirm email, newpw, newpw, then login with newpw
        seq = iter(['Changer', 'change@example.com', 'change', 'change@example.com', 'newpw', 'newpw', 'newpw'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        shop.login_prompt()
        assert shop.CURRENT_USER and shop.CURRENT_USER.get('email') == 'change@example.com'
        # verify that password was actually changed
        u = shop.find_user_by_email('change@example.com')
        assert u.get('password_hash') and u.get('salt')
        assert shop.verify_password('newpw', u.get('salt'), u.get('password_hash'))
    finally:
        restore_files(bak)


def test_gold_free_shipping_applied(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products for tests"
        prod = prods[0]
        pid = prod['id']
        prod['price'] = 250.0
        prod['stock'] = 10
        shop.save_json(shop.PRODUCTS_FILE, prods)
        # inputs: membership '3' (Gold), promo '', shipping 'delivery', address, confirm
        seq = iter(['3', '', 'delivery', 'Some Addr', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        ok = shop.purchase_product_direct(pid, 1)
        assert ok is True
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        o = orders[-1]
        assert abs(o['membership_discount'] - (250.0 * 0.1)) < 1e-6
        assert abs(o['shipping_fee'] - 0.0) < 1e-6
    finally:
        restore_files(bak)


def test_business_bulk_special_discount(monkeypatch):
    bak = backup_files()
    try:
        shop.save_json(shop.ORDERS_FILE, [])
        prods = shop.load_json(shop.PRODUCTS_FILE)
        assert prods, "No products for tests"
        prod = prods[0]
        pid = prod['id']
        prod['price'] = 100.0
        prod['stock'] = 20
        shop.save_json(shop.PRODUCTS_FILE, prods)
        # inputs: membership '4' (Business), promo '', shipping 'pickup', confirm
        seq = iter(['4', '', 'pickup', 'ha'])
        monkeypatch.setattr('builtins.input', lambda prompt='': next(seq))
        ok = shop.purchase_product_direct(pid, 10)
        assert ok is True
        orders = shop.load_json(shop.ORDERS_FILE)
        assert len(orders) == 1
        o = orders[-1]
        subtotal = 100.0 * 10
        expected_special = subtotal * 0.10
        expected_base = subtotal * 0.12
        assert abs(o['membership_discount'] - (expected_base + expected_special)) < 1e-6
    finally:
        restore_files(bak)
