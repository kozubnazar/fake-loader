import uuid
import random
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from typing import Sequence, Any
from faker import Faker

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from dotenv import load_dotenv

load_dotenv()

fake = Faker("en_US")
fake.seed_instance(42)

MYSQL = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": 3307,
    "user": os.getenv("MYSQL_USER", "appuser"),
    "password": os.getenv("MYSQL_PASSWORD", "apppass"),
    "database": os.getenv("MYSQL_DATABASE", "mysql_db"),
}

N_CATEGORIES = 100
N_BRANDS = 500
N_PRODUCTS = 5000
N_STOREGROUPS = 100
N_STORES_PER_GROUP = 10
N_TERMINALS_PER_STORE = 3
N_RECEIPTS = 70000
N_ITEMS_PER_RECEIPT = 3

MAX_CATEGORY_DEPTH = 3
MAX_STOREGROUP_DEPTH = 3


def sid(n: int) -> str:
    return str(n)


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def qty_val(is_refund: bool) -> Decimal:
    q = Decimal(random.randint(1, 5)).quantize(Decimal("0.0001"))
    return -q if is_refund else q


def insert_with_commit(
    conn: Connection,
    table_name: str,
    columns: list[str],
    values: Sequence[tuple[Any, ...]] | tuple[Any, ...],
) -> int:
    if not values:
        return 0

    if isinstance(values, tuple) and (len(values) == 0 or not isinstance(values[0], (tuple, list))):
        rows = [values]
    else:
        rows = list(values)

    df = pd.DataFrame(values, columns=columns)
    df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
    conn.commit()
    return len(values)


def mysql_engine():
    password = quote_plus(os.getenv("MYSQL_PASSWORD", "apppass"))
    return create_engine(
        f"mysql+pymysql://{MYSQL['user']}:{password}@{MYSQL['host']}:{MYSQL['port']}/{MYSQL['database']}",
        future=True,
    )


def build_hierarchy_rows(
    count: int,
    name_prefix: str,
    max_depth: int,
    parent_probability: float,
) -> list[tuple[str, str, str | None]]:
    rows: list[tuple[str, str, str | None]] = []
    levels: dict[int, int] = {}

    for node_id in range(1, count + 1):
        name = f"{name_prefix} {node_id}"

        if node_id == 1:
            parent_id: int | None = None
            depth = 1
        else:
            candidates = [pid for pid, d in levels.items() if d < max_depth]
            if candidates and random.random() < parent_probability:
                parent_id = random.choice(candidates)
                depth = levels[parent_id] + 1
            else:
                parent_id = None
                depth = 1

        levels[node_id] = depth
        rows.append((sid(node_id), name, sid(parent_id) if parent_id is not None else None))

    return rows


def main():
    random.seed(42)
    engine = mysql_engine()
    conn = engine.connect()

    try:

        # 1) Category
        category_rows = build_hierarchy_rows(
            count=N_CATEGORIES,
            name_prefix= "Category",
            max_depth=MAX_CATEGORY_DEPTH,
            parent_probability=0.7,
        )

        insert_with_commit(
            conn,
            "category",
            ["id", "name", "parent_id"],
            category_rows,
        )


        # 2) Brand
        brand_rows = []
        for bid in range(1, N_BRANDS + 1):
            name = fake.company()
            brand_rows.append((sid(bid), name))

        insert_with_commit(
            conn,
            "brand",
            ["id", "name"],
            brand_rows,
        )


        # 3) StoreGroup + Store
        storegroup_rows = build_hierarchy_rows(
            count=N_STOREGROUPS,
            name_prefix="StoreGroup",
            max_depth=MAX_STOREGROUP_DEPTH,
            parent_probability=0.33,
        )
      
        insert_with_commit(
            conn,
            "storegroup",
            ["id", "name", "parent_id"],
            storegroup_rows,
        )

        total_stores = N_STOREGROUPS * N_STORES_PER_GROUP
        store_rows = []
        for store_id in range(1, total_stores + 1):
            group_id = (store_id - 1) // N_STORES_PER_GROUP + 1
            idx_in_group = (store_id - 1) % N_STORES_PER_GROUP + 1
            store_name = f"Store G{group_id}-{idx_in_group}"
            store_rows.append((sid(store_id), store_name, sid(group_id)))

        insert_with_commit(
            conn,
            "store",
            ["id", "name", "group_id"],
            store_rows,
        )


        # 4) Terminal
        total_terminals = total_stores * N_TERMINALS_PER_STORE
        terminal_rows = []
        for terminal_id in range(1, total_terminals + 1):
            store_id = (terminal_id - 1) // N_TERMINALS_PER_STORE + 1
            t_name = f"Terminal {terminal_id}"
            terminal_rows.append((sid(terminal_id), t_name, sid(store_id)))

        insert_with_commit(
            conn,
            "terminal",
            ["id", "name", "store_id"],
            terminal_rows,
        )


        # 5) Product
        product_rows = []
        for product_id in range(1, N_PRODUCTS + 1):
            name = f"Product {product_id}"
            code = f"CODE-{10000 + product_id}"
            barcode = ",".join(
                str(random.randint(10**12, 10**13-1))
                for _ in range(random.choice([1, 1, 2]))
            )
            category_id = random.randint(1, N_CATEGORIES)
            
            product_rows.append((sid(product_id), name, code, barcode, sid(category_id)))

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

        for receipt_id in range(1, N_RECEIPTS + 1):
            store_id = random.randint(1, total_stores)
            terminal_offset = random.randint(1, N_TERMINALS_PER_STORE)
            terminal_id = (store_id - 1) * N_TERMINALS_PER_STORE + terminal_offset

            opened = now - timedelta(days=random.randint(0, 7), minutes=random.randint(0, 600))
            closed = opened + timedelta(minutes=random.randint(1, 120))

            receipt_rows.append((sid(receipt_id), sid(store_id), sid(terminal_id), opened, closed))
            receipt_ids.append((sid(receipt_id), closed))

        insert_with_commit(
            conn,
            "receipt",
            ["id", "store_id", "terminal_id", "opened_at", "closed_at"],
            receipt_rows,
        )

        # 7) ReceiptItem
        receipt_item_rows = []
        item_id = 1
        for receipt_id, r_closed in receipt_ids:
            is_refund = (random.random() < 0.15) 
            for _ in range(N_ITEMS_PER_RECEIPT):
                product_id = random.randint(1, N_PRODUCTS)

                price = money(random.uniform(10, 500))
                qty = qty_val(is_refund)
                turnover = (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                cost_price = money(float(price) * random.uniform(0.5, 0.9))

                receipt_item_rows.append(
                    (sid(item_id), receipt_id, sid(product_id), r_closed, str(price), str(qty), str(turnover), str(cost_price))
                )
                item_id += 1

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
