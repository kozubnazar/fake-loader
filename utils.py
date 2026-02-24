import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd
from faker import Faker
from sqlalchemy.engine import Connection


def sid(n: int) -> str:
    return str(n)


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def qty_val(is_refund: bool) -> Decimal:
    q = Decimal(random.randint(1, 5)).quantize(Decimal("0.0001"))
    return -q if is_refund else q


def insert_rows(
    conn: Connection,
    table_name: str,
    columns: list[str],
    values: list[tuple[Any, ...]],
) -> int:
    if not values:
        return 0
    df = pd.DataFrame(values, columns=columns)
    df.to_sql(table_name, conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return len(values)


def insert_with_commit(
    conn: Connection,
    table_name: str,
    columns: list[str],
    values: list[tuple[Any, ...]],
) -> int:
    inserted = insert_rows(conn, table_name, columns, values)
    conn.commit()
    return inserted


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
            parent_id = None
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


def generate_brand_rows(n_brands: int, fake: Faker) -> list[tuple[str, str]]:
    return [(sid(brand_id), fake.company()) for brand_id in range(1, n_brands + 1)]


def generate_store_rows(
    n_storegroups: int,
    n_stores_per_group: int,
) -> tuple[list[tuple[str, str, str]], int]:
    total_stores = n_storegroups * n_stores_per_group
    rows: list[tuple[str, str, str]] = []

    for store_id in range(1, total_stores + 1):
        group_id = (store_id - 1) // n_stores_per_group + 1
        idx_in_group = (store_id - 1) % n_stores_per_group + 1
        rows.append((sid(store_id), f"Store G{group_id}-{idx_in_group}", sid(group_id)))

    return rows, total_stores


def generate_terminal_rows(
    total_stores: int,
    n_terminals_per_store: int,
) -> list[tuple[str, str, str]]:
    total_terminals = total_stores * n_terminals_per_store
    rows: list[tuple[str, str, str]] = []

    for terminal_id in range(1, total_terminals + 1):
        store_id = (terminal_id - 1) // n_terminals_per_store + 1
        rows.append((sid(terminal_id), f"Terminal {terminal_id}", sid(store_id)))

    return rows


def generate_product_rows(
    n_products: int,
    n_categories: int,
) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []

    for product_id in range(1, n_products + 1):
        code = f"CODE-{10000 + product_id}"
        barcode = ",".join(
            str(random.randint(10**12, 10**13 - 1))
            for _ in range(random.choice([1, 1, 2]))
        )
        category_id = random.randint(1, n_categories)
        rows.append((sid(product_id), f"Product {product_id}", code, barcode, sid(category_id)))

    return rows


def build_receipt_and_item_batch(
    day_start: datetime,
    batch_size: int,
    receipt_id_counter: int,
    item_id_counter: int,
    total_stores: int,
    n_terminals_per_store: int,
    n_items_per_receipt: int,
    n_products: int,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], int, int]:
    receipt_rows: list[tuple[Any, ...]] = []
    receipt_item_rows: list[tuple[Any, ...]] = []

    for _ in range(batch_size):
        receipt_id = sid(receipt_id_counter)
        receipt_id_counter += 1

        store_id = random.randint(1, total_stores)
        terminal_offset = random.randint(1, n_terminals_per_store)
        terminal_id = (store_id - 1) * n_terminals_per_store + terminal_offset

        opened = day_start + timedelta(seconds=random.randint(0, 86399))
        closed = opened + timedelta(minutes=random.randint(1, 120))

        receipt_rows.append((receipt_id, sid(store_id), sid(terminal_id), opened, closed))

        is_refund = random.random() < 0.15
        for _ in range(n_items_per_receipt):
            product_id = random.randint(1, n_products)

            price = money(random.uniform(10, 500))
            qty = qty_val(is_refund)
            turnover = (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            cost_price = money(float(price) * random.uniform(0.5, 0.9))

            receipt_item_rows.append(
                (
                    sid(item_id_counter),
                    receipt_id,
                    sid(product_id),
                    closed,
                    str(price),
                    str(qty),
                    str(turnover),
                    str(cost_price),
                )
            )
            item_id_counter += 1

    return receipt_rows, receipt_item_rows, receipt_id_counter, item_id_counter
