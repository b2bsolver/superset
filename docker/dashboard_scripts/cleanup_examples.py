#!/usr/bin/env python3
"""
Cleanup Script - Remove All Example/Test Data
Removes all built-in example datasets and dashboards, keeping only custom MySQL tables
Run: docker exec superset_app python /app/docker/dashboard_scripts/cleanup_examples.py
"""
import sys
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Tables to keep (your custom tables)
KEEP_TABLES = [
    'otp_reports',
    'iycf_monthly_reports',
    'new_arrival_reports',
    'under_six_monthly_reports'
]

# Dashboards to keep (by slug)
KEEP_DASHBOARDS = [
    'otp-dashboard',
    'iycf-monthly-dashboard',
    'new-arrival-dashboard',
    'under-six-monthly-dashboard'
]

with app.app_context():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("=" * 80)
    print("CLEANUP: REMOVING EXAMPLE/TEST DATA")
    print("=" * 80)
    print("\nThis will remove all datasets and dashboards EXCEPT:")
    print("\nDatasets to keep:")
    for table in KEEP_TABLES:
        print(f"  - {table}")
    print("\nDashboards to keep:")
    for slug in KEEP_DASHBOARDS:
        print(f"  - {slug}")

    print("\n" + "=" * 80)
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)

    print("\n[1/4] Removing Example Dashboards...")
    dashboards_to_remove = db.session.query(Dashboard).filter(
        ~Dashboard.slug.in_(KEEP_DASHBOARDS)
    ).all()

    removed_dashboards = []
    for dashboard in dashboards_to_remove:
        removed_dashboards.append(dashboard.dashboard_title)
        # Remove all charts from dashboard first
        for slice in list(dashboard.slices):
            dashboard.slices.remove(slice)
        db.session.delete(dashboard)

    db.session.commit()
    print(f"✓ Removed {len(removed_dashboards)} dashboards:")
    for title in removed_dashboards:
        print(f"  - {title}")

    print("\n[2/4] Removing Orphaned Charts...")
    # Get IDs of charts that belong to kept dashboards
    kept_chart_ids = set()
    for dashboard in db.session.query(Dashboard).filter(Dashboard.slug.in_(KEEP_DASHBOARDS)).all():
        for slice in dashboard.slices:
            kept_chart_ids.add(slice.id)

    # Remove charts not in kept dashboards
    all_charts = db.session.query(Slice).all()
    removed_charts = []
    for chart in all_charts:
        if chart.id not in kept_chart_ids:
            removed_charts.append(chart.slice_name)
            db.session.delete(chart)

    db.session.commit()
    print(f"✓ Removed {len(removed_charts)} orphaned charts")

    print("\n[3/4] Removing Example Datasets...")
    datasets_to_remove = db.session.query(SqlaTable).filter(
        ~SqlaTable.table_name.in_(KEEP_TABLES)
    ).all()

    removed_datasets = []
    for dataset in datasets_to_remove:
        removed_datasets.append(dataset.table_name)
        db.session.delete(dataset)

    db.session.commit()
    print(f"✓ Removed {len(removed_datasets)} datasets:")
    for table in removed_datasets:
        print(f"  - {table}")

    print("\n[4/4] Removing Example Database Connections...")
    # Keep only MySQL database
    databases_to_remove = db.session.query(Database).filter(
        Database.database_name != 'MySQL'
    ).all()

    removed_databases = []
    for database in databases_to_remove:
        removed_databases.append(database.database_name)
        db.session.delete(database)

    db.session.commit()
    print(f"✓ Removed {len(removed_databases)} database connections:")
    for db_name in removed_databases:
        print(f"  - {db_name}")

    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE!")
    print("=" * 80)
    print("\nRemaining:")

    remaining_datasets = db.session.query(SqlaTable).all()
    print(f"\nDatasets ({len(remaining_datasets)}):")
    for dataset in remaining_datasets:
        print(f"  - {dataset.table_name}")

    remaining_dashboards = db.session.query(Dashboard).all()
    print(f"\nDashboards ({len(remaining_dashboards)}):")
    for dashboard in remaining_dashboards:
        print(f"  - {dashboard.dashboard_title} ({dashboard.slug})")

    remaining_databases = db.session.query(Database).all()
    print(f"\nDatabases ({len(remaining_databases)}):")
    for database in remaining_databases:
        print(f"  - {database.database_name}")

    print()
