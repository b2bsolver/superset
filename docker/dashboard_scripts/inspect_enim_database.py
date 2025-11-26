#!/usr/bin/env python3
"""
ENIM Database Schema Inspector
Directly connects to enim-core database to inspect table structures
Run: python docker/dashboard_scripts/inspect_enim_database.py --help
"""
import subprocess
import sys
import os

# Path to enim-core project (can be overridden via --path parameter or ENIM_CORE_PATH env var)
DEFAULT_ENIM_CORE_PATH = "../enim-core"
ENIM_CORE_PATH = os.getenv('ENIM_CORE_PATH', DEFAULT_ENIM_CORE_PATH)


def run_mysql_command(sql_query, database="enim_db"):
    """Execute MySQL command in enim-core database container"""
    cmd = [
        "docker", "compose", "exec", "db", "bash", "-c",
        f'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" {database} -e "{sql_query}" 2>&1 | grep -v "Warning"'
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=ENIM_CORE_PATH,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return None


def show_tables():
    """Show all tables in the database"""
    print(f"Using enim-core at: {ENIM_CORE_PATH}\n")
    print("=" * 80)
    print("ALL TABLES IN enim_db")
    print("=" * 80)
    result = run_mysql_command("SHOW TABLES;")
    if result:
        print(result)


def describe_table(table_name):
    """Describe a specific table structure"""
    print("\n" + "=" * 80)
    print(f"TABLE STRUCTURE: {table_name}")
    print("=" * 80)
    result = run_mysql_command(f"DESCRIBE {table_name};")
    if result:
        print(result)


def find_foreign_keys(table_name):
    """Find foreign key relationships for a table"""
    print("\n" + "=" * 80)
    print(f"FOREIGN KEYS: {table_name}")
    print("=" * 80)
    sql = f"""
    SELECT
        COLUMN_NAME,
        REFERENCED_TABLE_NAME,
        REFERENCED_COLUMN_NAME
    FROM
        INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
        TABLE_SCHEMA = 'enim_db'
        AND TABLE_NAME = '{table_name}'
        AND REFERENCED_TABLE_NAME IS NOT NULL;
    """
    result = run_mysql_command(sql, "information_schema")
    if result:
        print(result)


def get_sample_data(table_name, limit=5):
    """Get sample data from a table"""
    print("\n" + "=" * 80)
    print(f"SAMPLE DATA: {table_name} (first {limit} rows)")
    print("=" * 80)
    result = run_mysql_command(f"SELECT * FROM {table_name} LIMIT {limit};")
    if result:
        print(result)


def inspect_dashboard_tables():
    """Inspect all tables used in dashboards"""
    dashboard_tables = [
        'infs',
        'otp_reports',
        'sc_reports',
        'gmp_report_archives',
        'iycf_monthly_reports'
    ]

    print(f"Using enim-core at: {ENIM_CORE_PATH}\n")
    print("=" * 80)
    print("INSPECTING DASHBOARD TABLES")
    print("=" * 80)

    for table_name in dashboard_tables:
        describe_table(table_name)
        find_foreign_keys(table_name)
        print("\n")


def find_join_columns(table1, table2):
    """Find potential join columns between two tables"""
    print("\n" + "=" * 80)
    print(f"FINDING JOIN COLUMNS: {table1} <-> {table2}")
    print("=" * 80)

    # Get columns from both tables
    result1 = run_mysql_command(f"SHOW COLUMNS FROM {table1};")
    result2 = run_mysql_command(f"SHOW COLUMNS FROM {table2};")

    if result1 and result2:
        # Extract column names
        cols1 = [line.split('\t')[0] for line in result1.strip().split('\n')[1:]]
        cols2 = [line.split('\t')[0] for line in result2.strip().split('\n')[1:]]

        # Find common patterns
        print(f"\n{table1} columns containing 'id':")
        for col in cols1:
            if 'id' in col.lower():
                print(f"  - {col}")

        print(f"\n{table2} columns containing 'id':")
        for col in cols2:
            if 'id' in col.lower():
                print(f"  - {col}")

        # Check for foreign key pattern (table2_id in table1)
        potential_joins = []
        for col in cols1:
            if col.endswith('_id'):
                ref_table = col[:-3]  # Remove '_id'
                if ref_table in table2 or table2.startswith(ref_table):
                    potential_joins.append((col, 'id'))

        if potential_joins:
            print(f"\nPotential joins:")
            for col1, col2 in potential_joins:
                print(f"  {table1}.{col1} = {table2}.{col2}")


def main():
    """Main inspection function"""
    global ENIM_CORE_PATH

    args = sys.argv[1:]

    # Parse --path parameter if provided
    if '--path' in args:
        path_idx = args.index('--path')
        if path_idx + 1 < len(args):
            ENIM_CORE_PATH = args[path_idx + 1]
            # Remove --path and its value from args
            args.pop(path_idx)  # Remove --path
            args.pop(path_idx)  # Remove the path value
        else:
            print("Error: --path requires a value")
            print_usage()
            return

    if len(args) > 0:
        command = args[0]

        if command in ["help", "-h", "--help"]:
            print_usage()

        elif command == "tables":
            show_tables()

        elif command == "describe" and len(args) > 1:
            table_name = args[1]
            describe_table(table_name)
            find_foreign_keys(table_name)

        elif command == "sample" and len(args) > 1:
            table_name = args[1]
            limit = int(args[2]) if len(args) > 2 else 5
            get_sample_data(table_name, limit)

        elif command == "join" and len(args) > 2:
            table1 = args[1]
            table2 = args[2]
            find_join_columns(table1, table2)

        elif command == "dashboards":
            inspect_dashboard_tables()

        else:
            print("Unknown command!")
            print_usage()
    else:
        # Default: inspect all dashboard tables
        inspect_dashboard_tables()


def print_usage():
    """Print usage instructions"""
    print(f"""
Usage:
  python inspect_enim_database.py [--path <enim-core-path>] [command] [args]

Options:
  --path <path>             - Path to enim-core project directory
                              (Default: {DEFAULT_ENIM_CORE_PATH})
                              (Can also set via ENIM_CORE_PATH env var)

Commands:
  tables                    - List all tables
  describe <table>          - Describe table structure
  sample <table> [limit]    - Show sample data from table
  join <table1> <table2>    - Find join columns between tables
  dashboards                - Inspect all dashboard-related tables (default)

Examples:
  # Use default path
  python inspect_enim_database.py tables
  python inspect_enim_database.py describe infs
  python inspect_enim_database.py sample otp_reports 10
  python inspect_enim_database.py join otp_reports infs
  python inspect_enim_database.py dashboards

  # Use custom path
  python inspect_enim_database.py --path /custom/path/to/enim-core tables
  python inspect_enim_database.py --path /custom/path describe infs

  # Use environment variable
  export ENIM_CORE_PATH=/custom/path/to/enim-core
  python inspect_enim_database.py tables

Current path: {ENIM_CORE_PATH}
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
