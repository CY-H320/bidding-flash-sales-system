#!/usr/bin/env python3
"""
Check if the unique constraint on bidding_session_bids exists.
Run this to verify migrations were applied correctly.
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import engine


async def check_constraints():
    """Check for unique constraint on bidding_session_bids table."""
    async with engine.connect() as conn:
        # Query PostgreSQL system catalogs for constraints
        query = text("""
            SELECT
                con.conname AS constraint_name,
                con.contype AS constraint_type,
                ARRAY_AGG(att.attname ORDER BY u.attposition) AS columns
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN UNNEST(con.conkey) WITH ORDINALITY AS u(attnum, attposition) ON TRUE
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = u.attnum
            WHERE rel.relname = 'bidding_session_bids'
            AND nsp.nspname = 'public'
            AND con.contype = 'u'
            GROUP BY con.conname, con.contype
            ORDER BY con.conname;
        """)

        result = await conn.execute(query)
        constraints = result.fetchall()

        print("\n" + "="*70)
        print("🔍 Checking unique constraints on 'bidding_session_bids' table")
        print("="*70)

        if not constraints:
            print("❌ NO UNIQUE CONSTRAINTS FOUND!")
            print("\nYou need to run the migration:")
            print("   cd backend && .venv/bin/alembic upgrade head")
            return False

        found_session_user_constraint = False

        for constraint in constraints:
            name, type_code, columns = constraint
            columns_list = list(columns)

            print(f"\n✅ Found constraint: {name}")
            print(f"   Columns: {', '.join(columns_list)}")

            # Check if this is the constraint we need
            if set(columns_list) == {'session_id', 'user_id'}:
                found_session_user_constraint = True

        print("\n" + "="*70)

        if found_session_user_constraint:
            print("✅ SUCCESS: (session_id, user_id) unique constraint exists!")
            print("   Your UPSERT operations will work correctly.")
            return True
        else:
            print("❌ WARNING: (session_id, user_id) unique constraint NOT FOUND!")
            print("\nRun this migration:")
            print("   cd backend && .venv/bin/alembic upgrade head")
            return False


async def main():
    """Main function."""
    try:
        success = await check_constraints()
        await engine.dispose()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error checking constraints: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database credentials in .env are correct")
        print("3. Database exists")
        await engine.dispose()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
