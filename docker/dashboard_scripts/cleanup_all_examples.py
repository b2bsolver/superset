#!/usr/bin/env python3
"""
Complete Cleanup Script - Remove ALL Example/Test Data
Removes all built-in example datasets, dashboards, and charts
Keeps ONLY your custom MySQL report dashboards
Run: docker exec superset_app python /app/docker/dashboard_scripts/cleanup_all_examples.py
"""
import sys
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Dashboard IDs or slugs to keep (your custom dashboards)
KEEP_DASHBOARD_SLUGS = [
    'otp-dashboard',
    'iycf-monthly-dashboard',
    'new-arrival-dashboard',
    'under-six-monthly-dashboard'
]

# Tables to keep (your custom tables)
KEEP_TABLES = [
    'otp_reports',
    'iycf_monthly_reports',
    'new_arrival_reports',
    'under_six_monthly_reports'
]

with app.app_context():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("=" * 80)
    print("COMPLETE CLEANUP: REMOVING ALL EXAMPLE/TEST DATA")
    print("=" * 80)
    print("\nThis will remove ALL dashboards, charts, and datasets EXCEPT:")
    print("\nDashboards to keep:")
    for slug in KEEP_DASHBOARD_SLUGS:
        print(f"  - {slug}")
    print("\nDatasets to keep:")
    for table in KEEP_TABLES:
        print(f"  - {table}")

    print("\n" + "=" * 80)
    response = input("Continue? This cannot be undone! (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)

    print("\n[1/5] Finding Dashboards to Keep...")
    # Get dashboard IDs to keep
    kept_dashboards = db.session.query(Dashboard).filter(
        Dashboard.slug.in_(KEEP_DASHBOARD_SLUGS)
    ).all()

    keep_dashboard_ids = {d.id for d in kept_dashboards}
    print(f"✓ Found {len(keep_dashboard_ids)} dashboards to keep:")
    for dashboard in kept_dashboards:
        print(f"  - {dashboard.dashboard_title} (ID: {dashboard.id})")

    print("\n[2/5] Removing All Other Dashboards...")
    all_dashboards = db.session.query(Dashboard).all()
    removed_dashboards = []

    for dashboard in all_dashboards:
        if dashboard.id not in keep_dashboard_ids:
            removed_dashboards.append(f"{dashboard.dashboard_title or 'Untitled'} (ID: {dashboard.id})")
            # Clear all slices from dashboard
            for slice in list(dashboard.slices):
                dashboard.slices.remove(slice)
            db.session.delete(dashboard)

    db.session.commit()
    print(f"✓ Removed {len(removed_dashboards)} dashboards:")
    for title in removed_dashboards[:10]:  # Show first 10
        print(f"  - {title}")
    if len(removed_dashboards) > 10:
        print(f"  ... and {len(removed_dashboards) - 10} more")

    print("\n[3/5] Finding Charts to Keep...")
    # Get chart IDs that belong to kept dashboards
    kept_chart_ids = set()
    for dashboard in kept_dashboards:
        for slice in dashboard.slices:
            kept_chart_ids.add(slice.id)

    print(f"✓ Found {len(kept_chart_ids)} charts to keep")

    print("\n[4/5] Removing All Other Charts...")
    all_charts = db.session.query(Slice).all()
    removed_charts = []

    for chart in all_charts:
        if chart.id not in kept_chart_ids:
            removed_charts.append(f"{chart.slice_name} (ID: {chart.id})")
            db.session.delete(chart)

    db.session.commit()
    print(f"✓ Removed {len(removed_charts)} charts")

    print("\n[5/5] Removing All Other Datasets...")
    all_datasets = db.session.query(SqlaTable).all()
    removed_datasets = []

    for dataset in all_datasets:
        if dataset.table_name not in KEEP_TABLES:
            removed_datasets.append(f"{dataset.table_name} (ID: {dataset.id})")
            db.session.delete(dataset)

    db.session.commit()
    print(f"✓ Removed {len(removed_datasets)} datasets:")
    for table in removed_datasets[:10]:  # Show first 10
        print(f"  - {table}")
    if len(removed_datasets) > 10:
        print(f"  ... and {len(removed_datasets) - 10} more")

    print("\n[6/6] Removing Example Database Connections...")
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
    print("\n📊 Remaining Resources:")

    remaining_databases = db.session.query(Database).all()
    print(f"\n✓ Databases ({len(remaining_databases)}):")
    for database in remaining_databases:
        print(f"    - {database.database_name}")

    remaining_datasets = db.session.query(SqlaTable).all()
    print(f"\n✓ Datasets ({len(remaining_datasets)}):")
    for dataset in remaining_datasets:
        print(f"    - {dataset.table_name}")

    remaining_dashboards = db.session.query(Dashboard).all()
    print(f"\n✓ Dashboards ({len(remaining_dashboards)}):")
    for dashboard in remaining_dashboards:
        chart_count = len(dashboard.slices)
        print(f"    - {dashboard.dashboard_title} ({chart_count} charts)")

    total_charts = db.session.query(Slice).count()
    print(f"\n✓ Total Charts: {total_charts}")

    print("\n" + "=" * 80)
    print("Your Superset now only contains your custom MySQL report dashboards!")
    print("=" * 80)
    print()
