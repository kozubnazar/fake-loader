from datetime import datetime, time, timedelta

from connection import get_mysql_connection, get_postgres_connection
from utils import (
    copy_receipts_for_day,
    copy_receiptitems_for_day,
    copy_reference_table,
    create_postgres_schema,
    delete_documents_for_day,
    get_receipt_days,
)

REFERENCE_TABLES = {
    "category": ["id", "name", "parent_id"],
    "brand": ["id", "name"],
    "storegroup": ["id", "name", "parent_id"],
    "store": ["id", "name", "group_id", "trade_area", "place", "address"],
    "terminal": ["id", "name", "store_id"],
    "product": ["id", "name", "code", "barcode", "category_id"],
}

REF_CHUNK_SIZE = 5000
DOC_RECEIPT_CHUNK_SIZE = 5000
DOC_ITEM_CHUNK_SIZE = 10000


def main() -> None:
    mysql_conn = get_mysql_connection()
    pg_conn = get_postgres_connection()

    try:
        # 1) Створити порожню схему в PostgreSQL
        create_postgres_schema(pg_conn)
        pg_conn.commit()
        print("PostgreSQL schema is ready.")

        # 2) Довідники: тільки довантаження (upsert do nothing)
        for table_name, columns in REFERENCE_TABLES.items():
            inserted = copy_reference_table(
                mysql_conn=mysql_conn,
                pg_conn=pg_conn,
                table_name=table_name,
                columns=columns,
                chunk_size=REF_CHUNK_SIZE,
            )
            pg_conn.commit()
            print(f"[REF] {table_name}: processed {inserted} rows")

        # 3) Документи: перевантаження по днях
        days = get_receipt_days(mysql_conn)
        print(f"Document days to reload: {len(days)}")

        for day in days:
            day_start = datetime.combine(day, time.min)
            day_end = day_start + timedelta(days=1)

            try:
                delete_documents_for_day(pg_conn, day_start, day_end)

                receipts_count = copy_receipts_for_day(
                    mysql_conn=mysql_conn,
                    pg_conn=pg_conn,
                    day_start=day_start,
                    day_end=day_end,
                    chunk_size=DOC_RECEIPT_CHUNK_SIZE,
                )

                items_count = copy_receiptitems_for_day(
                    mysql_conn=mysql_conn,
                    pg_conn=pg_conn,
                    day_start=day_start,
                    day_end=day_end,
                    chunk_size=DOC_ITEM_CHUNK_SIZE,
                )

                pg_conn.commit()
                print(f"[DOC] {day}: receipts={receipts_count}, receipt_items={items_count}")
            except Exception:
                pg_conn.rollback()
                raise

        print("MySQL -> PostgreSQL pipeline completed successfully.")

    except Exception as exc:
        pg_conn.rollback()
        print(f"Pipeline failed: {exc}")
        raise
    finally:
        mysql_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
