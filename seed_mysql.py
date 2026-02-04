import uuid
import random
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta

import mysql.connector

MYSQL = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "appuser",
    "password": "apppass",
    "database": "mysql_db",
}

N_CATEGORIES = 5
N_BRANDS = 5
N_PRODUCTS = 20
N_STOREGROUPS = 3
N_STORES_PER_GROUP = 3
N_TERMINALS_PER_STORE = 3
N_RECEIPTS = 10
N_ITEMS_PER_RECEIPT = 3


ALL_PARENTS_NULL = True


def uid() -> str:
    return str(uuid.uuid4())


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def qty_val(is_refund: bool) -> Decimal:
    q = Decimal(random.randint(1, 5)).quantize(Decimal("0.0001"))
    return -q if is_refund else q


def main():
    random.seed(42)
    conn = mysql.connector.connect(**MYSQL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # clean code run
        # cur.execute("SET FOREIGN_KEY_CHECKS=0;")
        # for t in ["receiptitem","receipt","terminal","store","storegroup","product","brand","category"]:
        #     cur.execute(f"DELETE FROM `{t}`;")
        # cur.execute("SET FOREIGN_KEY_CHECKS=1;")

        # 1) Category
        category_ids = []
        for i in range(N_CATEGORIES):
            cid = uid()
            name = f"Category {i+1}"
            parent_id = None 
            cur.execute(
                "INSERT INTO category (id, name, parent_id) VALUES (%s, %s, %s)",
                (cid, name, parent_id),
            )
            category_ids.append(cid)

        # 2) Brand
        brand_ids = []
        for i in range(N_BRANDS):
            bid = uid()
            name = f"Brand {i+1}"
            cur.execute(
                "INSERT INTO brand (id, name) VALUES (%s, %s)",
                (bid, name),
            )
            brand_ids.append(bid)

        # 3) StoreGroup + Store
        storegroup_ids = []
        store_ids = []

        for i in range(N_STOREGROUPS):
            sgid = uid()
            sg_name = f"StoreGroup {i+1}"
            sg_parent = None 

            cur.execute(
                "INSERT INTO storegroup (id, name, parent_id) VALUES (%s, %s, %s)",
                (sgid, sg_name, sg_parent),
            )
            storegroup_ids.append(sgid)


            for j in range(N_STORES_PER_GROUP):
                sid = uid()
                s_name = f"Store G{i+1}-{j+1}"

                cur.execute(
                    "INSERT INTO store (id, name, group_id) VALUES (%s, %s, %s)",
                    (sid, s_name, sgid),
                )

                store_ids.append(sid)

        # 4) Terminal
        terminal_ids = []
        term_index = 1
        for sid in store_ids:
            for _ in range(N_TERMINALS_PER_STORE):
                tid = uid()
                t_name = f"Terminal {term_index}"
                term_index += 1
                cur.execute(
                    "INSERT INTO terminal (id, name, store_id) VALUES (%s, %s, %s)",
                    (tid, t_name, sid),
                )
                terminal_ids.append((tid, sid))

        # 5) Product
        product_ids = []
        for i in range(N_PRODUCTS):
            pid = uid()
            name = f"Product {i+1}"
            code = f"CODE-{10000+i}"
            barcode = ",".join(str(random.randint(10**12, 10**13-1)) for _ in range(random.choice([1, 1, 2])))
            category_id = random.choice(category_ids)
            cur.execute(
                "INSERT INTO product (id, name, code, barcode, category_id) VALUES (%s, %s, %s, %s, %s)",
                (pid, name, code, barcode, category_id),
            )
            product_ids.append(pid)

        # 6) Receipt
        receipt_ids = []
        now = datetime.now()

        for i in range(N_RECEIPTS):
            rid = uid()
            terminal_id, store_id = random.choice(terminal_ids)

            opened = now - timedelta(days=random.randint(0, 7), minutes=random.randint(0, 600))
            closed = opened + timedelta(minutes=random.randint(1, 120))

            cur.execute(
                "INSERT INTO receipt (id, store_id, terminal_id, opened_at, closed_at) VALUES (%s, %s, %s, %s, %s)",
                (rid, store_id, terminal_id, opened, closed),
            )
            receipt_ids.append((rid, closed))

        # 7) ReceiptItem
        for rid, r_closed in receipt_ids:
            is_refund = (random.random() < 0.15) 
            for _ in range(N_ITEMS_PER_RECEIPT):
                riid = uid()
                product_id = random.choice(product_ids)

                price = money(random.uniform(10, 500))
                qty = qty_val(is_refund)
                turnover = (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                cost_price = money(float(price) * random.uniform(0.5, 0.9))

                cur.execute(
                    """
                    INSERT INTO receiptitem
                      (id, receipt_id, product_id, receipt_closed_at, price, qty, turnover, cost_price)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (riid, rid, product_id, r_closed, str(price), str(qty), str(turnover), str(cost_price)),
                )

        conn.commit()
        print("✅ Seed complete: MySQL tables filled successfully.")

    except Exception as e:
        conn.rollback()
        print("❌ Seed failed:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
