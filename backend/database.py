"""
Database Management & Cleanup Module for BoxnFreight Triage SQLite Database.

Provides administrative utilities for cleaning spam, gibberish, and non-persisting
conversational greeting records from the tickets table to keep the operational
queues clean and genuine.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("boxnfreight.database")

DB_PATH = Path(__file__).resolve().parent / "tickets.db"


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Returns a standard sqlite3 connection with Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_ticket_counts_by_status(conn: sqlite3.Connection) -> Dict[str, int]:
    """Returns a dictionary of ticket counts grouped by status."""
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
    return {row["status"]: row["count"] for row in cursor.fetchall()}


def cleanup_tickets_database(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Purges spam, gibberish, and conversational greeting test tickets from SQLite database:
      1. description LIKE '%jhhhhh%'
      2. description LIKE '%khflivfly%'
      3. category = 'Conversational Greeting / Inquiry'
      4. LENGTH(TRIM(description)) < 4
      5. Secondary verification using is_gibberish_or_spam heuristics

    Ensures the SQLite database is committed and vacuumed so Admin Console
    reflects clean genuine counts immediately.
    """
    logger.info(f"Connecting to tickets database at: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Pre-cleanup stats
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_before = cursor.fetchone()[0]
        stats_before = get_ticket_counts_by_status(conn)
        logger.info(f"Total tickets before cleanup: {total_before} | Breakdown: {stats_before}")

        # 1. Fetch targeted spam & greeting records for logging
        cursor.execute(
            """
            SELECT id, reference_id, category, description, status
            FROM tickets
            WHERE description LIKE '%jhhhhh%'
               OR description LIKE '%khflivfly%'
               OR category = 'Conversational Greeting / Inquiry'
               OR LENGTH(TRIM(description)) < 4
            """
        )
        targeted_rows = cursor.fetchall()
        logger.info(f"Found {len(targeted_rows)} tickets matching primary SQL purge criteria.")
        for r in targeted_rows:
            logger.info(f"  [PURGE TARGET] ID={r['id']} ({r['reference_id']}) Status={r['status']} Cat='{r['category']}' Desc='{r['description']}'")

        # 2. Execute Primary SQL Purge
        cursor.execute(
            """
            DELETE FROM tickets
            WHERE description LIKE '%jhhhhh%'
               OR description LIKE '%khflivfly%'
               OR category = 'Conversational Greeting / Inquiry'
               OR LENGTH(TRIM(description)) < 4
            """
        )
        sql_deleted_count = cursor.rowcount
        logger.info(f"Executed primary SQL DELETE: {sql_deleted_count} rows removed.")

        # 3. Secondary pass: Check any remaining records with is_gibberish_or_spam heuristic
        try:
            from agent import is_gibberish_or_spam
            cursor.execute("SELECT id, reference_id, description FROM tickets")
            remaining_rows = cursor.fetchall()
            gibberish_ids = [
                row["id"] for row in remaining_rows
                if is_gibberish_or_spam(row["description"])
            ]
            if gibberish_ids:
                placeholders = ",".join("?" for _ in gibberish_ids)
                cursor.execute(f"DELETE FROM tickets WHERE id IN ({placeholders})", gibberish_ids)
                logger.info(f"Secondary heuristic purge: {len(gibberish_ids)} additional spam tickets removed.")
        except ImportError:
            logger.warning("agent.py not available in path for secondary heuristic check; primary SQL purge complete.")

        # 4. Commit changes and vacuum database
        conn.commit()
        cursor.execute("VACUUM")
        conn.commit()

        # Post-cleanup stats
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_after = cursor.fetchone()[0]
        stats_after = get_ticket_counts_by_status(conn)
        purged_total = total_before - total_after

        logger.info(f"Cleanup successfully completed!")
        logger.info(f"Total tickets purged: {purged_total}")
        logger.info(f"Remaining genuine tickets: {total_after} | Breakdown: {stats_after}")

        return {
            "success": True,
            "total_before": total_before,
            "total_after": total_after,
            "purged_count": purged_total,
            "breakdown_before": stats_before,
            "breakdown_after": stats_after,
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error during tickets database cleanup: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    result = cleanup_tickets_database()
    print("\n" + "=" * 50)
    print("BOXNFREIGHT TICKETS DATABASE CLEANUP SUMMARY")
    print("=" * 50)
    print(f"Total Tickets (Before): {result['total_before']}")
    print(f"Total Purged:           {result['purged_count']}")
    print(f"Genuine Tickets Left:   {result['total_after']}")
    print(f"Final Breakdown:        {result['breakdown_after']}")
    print("=" * 50)
