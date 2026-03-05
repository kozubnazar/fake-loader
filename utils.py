import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd
from faker import Faker
from sqlalchemy import text
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

def create_postgres_schema(pg_conn: Connection) -> None:
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS category (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            parent_id VARCHAR(100) NULL,
            CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES category(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS brand (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS storegroup (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            parent_id VARCHAR(100) NULL,
            CONSTRAINT fk_storegroup_parent FOREIGN KEY (parent_id) REFERENCES storegroup(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS store (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            group_id VARCHAR(100) NULL,
            trade_area NUMERIC(20,4) NULL,
            place VARCHAR(200) NULL,
            address VARCHAR(200) NULL,
            CONSTRAINT fk_store_group FOREIGN KEY (group_id) REFERENCES storegroup(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS terminal (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            store_id VARCHAR(100) NOT NULL,
            CONSTRAINT fk_terminal_store FOREIGN KEY (store_id) REFERENCES store(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            code VARCHAR(100) NOT NULL,
            barcode TEXT NULL,
            category_id VARCHAR(100) NOT NULL,
            CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS receipt (
            id VARCHAR(100) PRIMARY KEY,
            store_id VARCHAR(100) NOT NULL,
            terminal_id VARCHAR(100) NOT NULL,
            opened_at TIMESTAMP NOT NULL,
            closed_at TIMESTAMP NOT NULL,
            CONSTRAINT fk_receipt_store FOREIGN KEY (store_id) REFERENCES store(id),
            CONSTRAINT fk_receipt_terminal FOREIGN KEY (terminal_id) REFERENCES terminal(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS receiptitem (
            id VARCHAR(100) PRIMARY KEY,
            receipt_id VARCHAR(100) NOT NULL,
            product_id VARCHAR(100) NOT NULL,
            receipt_closed_at TIMESTAMP NOT NULL,
            price NUMERIC(20,4) NOT NULL,
            qty NUMERIC(20,4) NOT NULL,
            turnover NUMERIC(20,4) NOT NULL,
            cost_price NUMERIC(20,4) NOT NULL,
            CONSTRAINT fk_receiptitem_receipt FOREIGN KEY (receipt_id) REFERENCES receipt(id),
            CONSTRAINT fk_receiptitem_product FOREIGN KEY (product_id) REFERENCES product(id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_category_parent ON category(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_storegroup_parent ON storegroup(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_store_group ON store(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_terminal_store ON terminal(store_id)",
        "CREATE INDEX IF NOT EXISTS idx_product_category ON product(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_receipt_store ON receipt(store_id)",
        "CREATE INDEX IF NOT EXISTS idx_receipt_terminal ON receipt(terminal_id)",
        "CREATE INDEX IF NOT EXISTS idx_receipt_opened ON receipt(opened_at)",
        "CREATE INDEX IF NOT EXISTS idx_receiptitem_receipt ON receiptitem(receipt_id)",
        "CREATE INDEX IF NOT EXISTS idx_receiptitem_product ON receiptitem(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_receiptitem_closed ON receiptitem(receipt_closed_at)",
    ]

    for stmt in ddl_statements:
        pg_conn.execute(text(stmt))

def _to_records_with_nulls(df: pd.DataFrame) -> list[dict[str, Any]]:
    normalized = df.astype(object).where(pd.notna(df), None)
    return normalized.to_dict(orient="records")


def copy_reference_table(
    mysql_conn: Connection,
    pg_conn: Connection,
    table_name: str,
    columns: list[str],
    chunk_size: int = 5000,
) -> int:
    # Для self-parent таблиць батьки (NULL) йдуть першими, далі по id
    if table_name in {"category", "storegroup"} and "parent_id" in columns:
        order_sql = "CASE WHEN parent_id IS NULL THEN 0 ELSE 1 END, CAST(id AS UNSIGNED)"
    else:
        order_sql = "CAST(id AS UNSIGNED)"

    query = f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY {order_sql}"
    total = 0

    cols_sql = ", ".join(columns)
    vals_sql = ", ".join(f":{c}" for c in columns)
    upsert_sql = text(
        f"""
        INSERT INTO {table_name} ({cols_sql})
        VALUES ({vals_sql})
        ON CONFLICT (id) DO NOTHING
        """
    )

    for chunk in pd.read_sql_query(text(query), mysql_conn, chunksize=chunk_size):
        if chunk.empty:
            continue

        rows = _to_records_with_nulls(chunk)
        pg_conn.execute(upsert_sql, rows)
        total += len(rows)

    return total


def get_receipt_days(mysql_conn: Connection) -> list:
    rows = mysql_conn.execute(
        text(
            """
            SELECT DATE(opened_at) AS day_value
            FROM receipt
            GROUP BY DATE(opened_at)
            ORDER BY DATE(opened_at)
            """
        )
    ).fetchall()
    return [row[0] for row in rows]


def delete_documents_for_day(pg_conn: Connection, day_start: datetime, day_end: datetime) -> None:
    pg_conn.execute(
        text(
            """
            DELETE FROM receiptitem ri
            USING receipt r
            WHERE ri.receipt_id = r.id
              AND r.opened_at >= :day_start
              AND r.opened_at < :day_end
            """
        ),
        {"day_start": day_start, "day_end": day_end},
    )

    pg_conn.execute(
        text(
            """
            DELETE FROM receipt
            WHERE opened_at >= :day_start
              AND opened_at < :day_end
            """
        ),
        {"day_start": day_start, "day_end": day_end},
    )


def copy_receipts_for_day(
    mysql_conn: Connection,
    pg_conn: Connection,
    day_start: datetime,
    day_end: datetime,
    chunk_size: int = 5000,
) -> int:
    query = text(
        """
        SELECT id, store_id, terminal_id, opened_at, closed_at
        FROM receipt
        WHERE opened_at >= :day_start
          AND opened_at < :day_end
        ORDER BY opened_at, id
        """
    )

    total = 0
    for chunk in pd.read_sql_query(
        query,
        mysql_conn,
        params={"day_start": day_start, "day_end": day_end},
        chunksize=chunk_size,
    ):
        if chunk.empty:
            continue
        chunk.to_sql("receipt", pg_conn, if_exists="append", index=False, method="multi", chunksize=chunk_size)
        total += len(chunk)

    return total


def copy_receiptitems_for_day(
    mysql_conn: Connection,
    pg_conn: Connection,
    day_start: datetime,
    day_end: datetime,
    chunk_size: int = 10000,
) -> int:
    query = text(
        """
        SELECT ri.id, ri.receipt_id, ri.product_id, ri.receipt_closed_at, ri.price, ri.qty, ri.turnover, ri.cost_price
        FROM receiptitem ri
        JOIN receipt r ON r.id = ri.receipt_id
        WHERE r.opened_at >= :day_start
          AND r.opened_at < :day_end
        ORDER BY ri.receipt_closed_at, ri.id
        """
    )

    total = 0
    for chunk in pd.read_sql_query(
        query,
        mysql_conn,
        params={"day_start": day_start, "day_end": day_end},
        chunksize=chunk_size,
    ):
        if chunk.empty:
            continue
        chunk.to_sql("receiptitem", pg_conn, if_exists="append", index=False, method="multi", chunksize=chunk_size)
        total += len(chunk)

    return total