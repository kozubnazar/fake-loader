import uuid
import random
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

MYSQL = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "appuser",
    "password": os.getenv("MYSQL_PASSWORD", "apppass"),
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


def uid() -> str:
    return str(uuid.uuid4())


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def qty_val(is_refund: bool) -> Decimal:
    q = Decimal(random.randint(1, 5)).quantize(Decimal("0.0001"))
    return -q if is_refund else q


def insert_with_commit(conn, table_name, columns, values):
    if not values:
        return
    if isinstance(values, tuple):
        values = [values]
    df = pd.DataFrame(values, columns=columns)
    df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
    conn.commit()


def mysql_engine():
    password = quote_plus(os.getenv("MYSQL_PASSWORD", "apppass"))
    return create_engine(
        f"mysql+pymysql://{MYSQL['user']}:{password}@{MYSQL['host']}:{MYSQL['port']}/{MYSQL['database']}",
        future=True,
    )


def main():
    random.seed(42)
    engine = mysql_engine()
    conn = engine.connect()

    try:
        # clean code run
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        for t in ["receiptitem","receipt","terminal","store","storegroup","product","brand","category"]:
            conn.execute(text(f"DELETE FROM `{t}`;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
        conn.commit()
        
        # 1) Category
        category_ids = []
        category_rows = []
        for i in range(N_CATEGORIES):
            cid = uid()
            name = f"Category {i+1}"
            parent_id = None 
            category_rows.append((cid, name, parent_id))
            category_ids.append(cid)

        insert_with_commit(
            conn,
            "category",
            ["id", "name", "parent_id"],
            category_rows,
        )


        # 2) Brand
        brand_rows = []
        for i in range(N_BRANDS):
            bid = uid()
            name = f"Brand {i+1}"
            brand_rows.append((bid, name))

        insert_with_commit(
            conn,
            "brand",
            ["id", "name"],
            brand_rows,
        )


        # 3) StoreGroup + Store
        storegroup_ids = []
        store_ids = []
        storegroup_rows = []
        store_rows = []

        for i in range(N_STOREGROUPS):
            sgid = uid()
            sg_name = f"StoreGroup {i+1}"
            sg_parent = None
            
            storegroup_rows.append((sgid, sg_name, sg_parent))
            storegroup_ids.append(sgid)

            for j in range(N_STORES_PER_GROUP):
                sid = uid()
                s_name = f"Store G{i+1}-{j+1}"
                
                store_rows.append((sid, s_name, sgid))
                store_ids.append(sid)
                
                
        insert_with_commit(
            conn,
            "storegroup",
            ["id", "name", "parent_id"],
            storegroup_rows,
        )

        insert_with_commit(
            conn,
            "store",
            ["id", "name", "group_id"],
            store_rows,
        )


        # 4) Terminal
        terminal_ids = []
        terminal_rows = []
        term_index = 1
        for sid in store_ids:
            for _ in range(N_TERMINALS_PER_STORE):
                tid = uid()
                t_name = f"Terminal {term_index}"
                term_index += 1
                terminal_rows.append((tid, t_name, sid))
                terminal_ids.append((tid, sid))

        insert_with_commit(
            conn,
            "terminal",
            ["id", "name", "store_id"],
            terminal_rows,
        )


        # 5) Product
        product_ids = []
        product_rows = []
        for i in range(N_PRODUCTS):
            pid = uid()
            name = f"Product {i+1}"
            code = f"CODE-{10000+i}"
            barcode = ",".join(
                str(random.randint(10**12, 10**13-1))
                for _ in range(random.choice([1, 1, 2]))
            )
            category_id = random.choice(category_ids)
            
            product_rows.append((pid, name, code, barcode, category_id))
            product_ids.append(pid)

        insert_with_commit(
            conn,
            "product",
            ["id", "name", "code", "barcode", "category_id"],
            product_rows,
        )


        # 6) Receipt
        receipt_ids = []
        receipt_rows = []
        now = datetime.now()

        for i in range(N_RECEIPTS):
            rid = uid()
            terminal_id, store_id = random.choice(terminal_ids)

            opened = now - timedelta(days=random.randint(0, 7), minutes=random.randint(0, 600))
            closed = opened + timedelta(minutes=random.randint(1, 120))

            receipt_rows.append((rid, store_id, terminal_id, opened, closed))
            receipt_ids.append((rid, closed))

        insert_with_commit(
            conn,
            "receipt",
            ["id", "store_id", "terminal_id", "opened_at", "closed_at"],
            receipt_rows,
        )

        # 7) ReceiptItem
        receipt_item_rows = []
        for rid, r_closed in receipt_ids:
            is_refund = (random.random() < 0.15) 
            for _ in range(N_ITEMS_PER_RECEIPT):
                riid = uid()
                product_id = random.choice(product_ids)

                price = money(random.uniform(10, 500))
                qty = qty_val(is_refund)
                turnover = (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                cost_price = money(float(price) * random.uniform(0.5, 0.9))

                receipt_item_rows.append(
                    (riid, rid, product_id, r_closed, str(price), str(qty), str(turnover), str(cost_price))
                )

        insert_with_commit(
            conn,
            "receiptitem",
            ["id", "receipt_id", "product_id", "receipt_closed_at", "price", "qty", "turnover", "cost_price"],
            receipt_item_rows,
        )

        print("Seed complete: MySQL tables filled successfully.")

    except Exception as e:
        print("Seed failed:", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
