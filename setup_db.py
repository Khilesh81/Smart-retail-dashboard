"""
setup_db.py — Run this ONCE after installing PostgreSQL to create the database
and apply the schema. 

Usage:
    python setup_db.py
    python setup_db.py --password yourpassword
"""
import sys
import os
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Setup retail_db PostgreSQL database")
    parser.add_argument("--host",     default="localhost",  help="DB host (default: localhost)")
    parser.add_argument("--port",     default="5432",       help="DB port (default: 5432)")
    parser.add_argument("--user",     default="postgres",   help="DB user (default: postgres)")
    parser.add_argument("--password", default="postgres",   help="DB password (default: postgres)")
    parser.add_argument("--dbname",   default="retail_db",  help="DB name (default: retail_db)")
    args = parser.parse_args()

    # Write .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "w") as f:
        f.write(f"DB_HOST={args.host}\n")
        f.write(f"DB_NAME={args.dbname}\n")
        f.write(f"DB_USER={args.user}\n")
        f.write(f"DB_PASSWORD={args.password}\n")
        f.write(f"DB_PORT={args.port}\n")
    print(f"✅ .env written at {env_path}")

    # Try to create the database
    try:
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Connect to postgres (default maintenance db)
        conn = psycopg2.connect(
            host=args.host, port=args.port,
            user=args.user, password=args.password,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Create DB if not exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (args.dbname,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(args.dbname)))
            print(f"✅ Database '{args.dbname}' created.")
        else:
            print(f"ℹ️  Database '{args.dbname}' already exists.")

        cur.close()
        conn.close()

        # Apply schema
        conn2 = psycopg2.connect(
            host=args.host, port=args.port,
            user=args.user, password=args.password,
            database=args.dbname
        )
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            schema_sql = f.read()
        with conn2.cursor() as cur2:
            cur2.execute(schema_sql)
        conn2.commit()
        conn2.close()
        print("✅ Schema applied successfully.")
        print("\n🚀 Database is ready! Run: streamlit run app.py")

    except psycopg2.OperationalError as e:
        print(f"\n❌ Could not connect to PostgreSQL: {e}")
        print("\n📋 Make sure PostgreSQL is installed and running:")
        print("   1. Install: https://www.postgresql.org/download/windows/")
        print("   2. Set password to 'postgres' during install (or pass --password)")
        print("   3. Start service: net start postgresql-x64-17")
        print("   4. Re-run: python setup_db.py --password <your_password>")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
