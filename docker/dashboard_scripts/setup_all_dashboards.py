#!/usr/bin/env python3
"""
Master Script - Setup All Report Dashboards
Runs all individual dashboard setup scripts
Run: docker exec superset_app python /app/docker/dashboard_scripts/setup_all_dashboards.py
"""
import sys
import os
import subprocess

SCRIPTS_DIR = '/app/docker/dashboard_scripts'

scripts = [
    'setup_iycf_dashboard.py',
    'setup_new_arrival_dashboard.py',
    'setup_under_six_dashboard.py'
]

print("=" * 80)
print("SETTING UP ALL REPORT DASHBOARDS")
print("=" * 80)
print()

total_scripts = len(scripts)
success_count = 0
failed_scripts = []

for i, script in enumerate(scripts, 1):
    script_path = os.path.join(SCRIPTS_DIR, script)
    print(f"[{i}/{total_scripts}] Running {script}...")
    print("-" * 80)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            check=True
        )
        success_count += 1
        print()
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to run {script}")
        failed_scripts.append(script)
        print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total Scripts: {total_scripts}")
print(f"Successful: {success_count}")
print(f"Failed: {len(failed_scripts)}")

if failed_scripts:
    print("\nFailed Scripts:")
    for script in failed_scripts:
        print(f"  - {script}")
    sys.exit(1)
else:
    print("\n✓ All dashboards created successfully!")
    print("\nDashboard URLs:")
    print("  - IYCF: http://localhost:8088/superset/dashboard/iycf-monthly-dashboard/")
    print("  - New Arrivals: http://localhost:8088/superset/dashboard/new-arrival-dashboard/")
    print("  - Under Six: http://localhost:8088/superset/dashboard/under-six-monthly-dashboard/")
    print()
