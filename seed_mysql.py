import random

from datetime import datetime, timedelta
from faker import Faker

from connection import get_mysql_connection
from utils import (
    build_hierarchy_rows,
    build_receipt_and_item_batch,
    insert_with_commit,
    insert_rows,
    generate_brand_rows,
    generate_product_rows,
    generate_store_rows,
    generate_terminal_rows,
)


fake = Faker("en_US")
fake.seed_instance(42)


N_CATEGORIES = 100
N_BRANDS = 500
N_PRODUCTS = 5000
N_STOREGROUPS = 100
N_STORES_PER_GROUP = 10
N_TERMINALS_PER_STORE = 3
N_ITEMS_PER_RECEIPT = 3

MAX_CATEGORY_DEPTH = 3
MAX_STOREGROUP_DEPTH = 3

RECEIPT_DAYS = 31
RECEIPTS_PER_DAY = 70000
RECEIPT_BATCH_SIZE = 5000


def main():
    random.seed(42)
    conn = get_mysql_connection()

    try:
        # 1) Category
        category_rows = build_hierarchy_rows(
            count=N_CATEGORIES,
            name_prefix="Category",
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
        brand_rows = generate_brand_rows(N_BRANDS, fake)

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

        store_rows, total_stores = generate_store_rows(N_STOREGROUPS, N_STORES_PER_GROUP)

        insert_with_commit(
            conn,
            "store",
            ["id", "name", "group_id"],
            store_rows,
        )


        # 4) Terminal
        terminal_rows = generate_terminal_rows(total_stores, N_TERMINALS_PER_STORE)

        insert_with_commit(
            conn,
            "terminal",
            ["id", "name", "store_id"],
            terminal_rows,
        )


        # 5) Product
        product_rows = generate_product_rows(N_PRODUCTS, N_CATEGORIES)

        insert_with_commit(
            conn,
            "product",
            ["id", "name", "code", "barcode", "category_id"],
            product_rows,
        )


        # 6) Receipt
        receipt_id_counter = 1
        item_id_counter = 1
        month_start = (datetime.now() - timedelta(days=RECEIPT_DAYS - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        for day_idx in range(RECEIPT_DAYS):
            day_start = month_start + timedelta(days=day_idx)
            receipts_left = RECEIPTS_PER_DAY

            while receipts_left > 0:
                batch_size = min(RECEIPT_BATCH_SIZE, receipts_left)

                receipt_rows, receipt_item_rows, receipt_id_counter, item_id_counter = build_receipt_and_item_batch(
                    day_start=day_start,
                    batch_size=batch_size,
                    receipt_id_counter=receipt_id_counter,
                    item_id_counter=item_id_counter,
                    total_stores=total_stores,
                    n_terminals_per_store=N_TERMINALS_PER_STORE,
                    n_items_per_receipt=N_ITEMS_PER_RECEIPT,
                    n_products=N_PRODUCTS,
                )


                try:
                    insert_rows(
                        conn,
                        "receipt",
                        ["id", "store_id", "terminal_id", "opened_at", "closed_at"],
                        receipt_rows,
                    )
                    insert_rows(
                        conn,
                        "receiptitem",
                        ["id", "receipt_id", "product_id", "receipt_closed_at", "price", "qty", "turnover", "cost_price"],
                        receipt_item_rows,
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

                receipts_left -= batch_size

            print(f"Day {day_idx + 1}/{RECEIPT_DAYS} done")                

        print("Seed complete: MySQL tables filled successfully.")

    except Exception as e:
        print("Seed failed:", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
