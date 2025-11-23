#!/usr/bin/env python3
"""
IYCF Monthly Reports Dashboard Setup
Creates dataset and dashboard with all charts from scratch
Run: docker exec superset_app python /app/docker/dashboard_scripts/setup_iycf_dashboard.py
"""
import sys
import json
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Configuration
TABLE_NAME = 'iycf_monthly_reports'
DASHBOARD_TITLE = 'IYCF Monthly Dashboard'
DASHBOARD_SLUG = 'iycf-monthly-dashboard'
DATABASE_NAME = 'MySQL'

with app.app_context():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("=" * 80)
    print(f"IYCF MONTHLY REPORTS DASHBOARD SETUP")
    print("=" * 80)

    # Step 1: Get Database
    print("\n[1/4] Finding Database...")
    database = db.session.query(Database).filter_by(database_name=DATABASE_NAME).first()
    if not database:
        print(f"✗ Database '{DATABASE_NAME}' not found!")
        sys.exit(1)
    print(f"✓ Found database '{DATABASE_NAME}' (ID: {database.id})")

    # Step 2: Create/Update Dataset
    print(f"\n[2/4] Setting up Dataset...")
    dataset = db.session.query(SqlaTable).filter_by(
        database_id=database.id,
        table_name=TABLE_NAME
    ).first()

    if dataset:
        print(f"  ℹ Dataset '{TABLE_NAME}' already exists (ID: {dataset.id})")
        # Refresh metadata
        dataset.fetch_metadata()
        db.session.commit()
        print(f"  ✓ Refreshed dataset metadata")
    else:
        dataset = SqlaTable(
            table_name=TABLE_NAME,
            database=database,
            schema=''
        )
        db.session.add(dataset)
        db.session.commit()
        dataset.fetch_metadata()
        db.session.commit()
        print(f"✓ Created dataset '{TABLE_NAME}' (ID: {dataset.id})")

    # Step 3: Create/Update Dashboard
    print(f"\n[3/4] Setting up Dashboard...")
    dashboard = db.session.query(Dashboard).filter_by(slug=DASHBOARD_SLUG).first()

    if dashboard:
        print(f"  ℹ Dashboard '{DASHBOARD_TITLE}' already exists (ID: {dashboard.id})")
        # Clear existing charts
        for slice in list(dashboard.slices):
            dashboard.slices.remove(slice)
            db.session.delete(slice)
        db.session.commit()
        print(f"  ✓ Cleared {len(list(dashboard.slices))} existing charts")
    else:
        dashboard = Dashboard(
            dashboard_title=DASHBOARD_TITLE,
            slug=DASHBOARD_SLUG,
            published=True
        )
        db.session.add(dashboard)
        db.session.commit()
        print(f"✓ Created dashboard '{DASHBOARD_TITLE}' (ID: {dashboard.id})")

    # Step 4: Create Charts
    print(f"\n[4/4] Creating Charts...")

    charts = []

    # Big Number 1: Total Staff Trained
    charts.append(Slice(
        slice_name='Total Staff Trained',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(staff_trained_todate)',
                'label': 'Total Staff Trained',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.3,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.0f'
        })
    ))

    # Big Number 2: Total Counselors Trained
    charts.append(Slice(
        slice_name='Total Counselors Trained',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(counselors_trained_todate)',
                'label': 'Total Counselors Trained',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.3,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.0f'
        })
    ))

    # Big Number 3: Total Volunteers Trained
    charts.append(Slice(
        slice_name='Total Volunteers Trained',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(volunteers_trained_todate)',
                'label': 'Total Volunteers Trained',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.3,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.0f'
        })
    ))

    # Big Number 4: Total IYCF Services
    charts.append(Slice(
        slice_name='Total IYCF Services',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(received_iycf_services)',
                'label': 'Total IYCF Services',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.3,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.0f'
        })
    ))

    # Big Number 5: Issues Resolved
    charts.append(Slice(
        slice_name='Issues Resolved (6-23m)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(issues_resolved_6_23m)',
                'label': 'Issues Resolved',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.3,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.0f'
        })
    ))

    # Line Chart: Monthly Training Progress
    charts.append(Slice(
        slice_name='Monthly Training Progress',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_line',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_line',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(staff_trained_period)',
                    'label': 'Staff Trained',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(counselors_trained_period)',
                    'label': 'Counselors Trained',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(volunteers_trained_period)',
                    'label': 'Volunteers Trained',
                    'hasCustomLabel': True
                }
            ],
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 10000,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'top',
            'rich_tooltip': True,
            'y_axis_format': ',.1f',
            'markerSize': 6,
            'truncateXAxis': True,
            'x_axis_time_format': 'smart_date'
        })
    ))

    # Bar Chart: Counseling Sessions
    charts.append(Slice(
        slice_name='Counseling Sessions',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(pw_counseled_1st_visit + pw_counseled_gt1_visit)',
                    'label': 'Pregnant Women',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(cg_0_5_counseled_1st_visit + cg_0_5_counseled_gt1_visit)',
                    'label': 'Caregivers 0-5m',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(cg_6_23_counseled_1st_visit + cg_6_23_counseled_gt1_visit)',
                    'label': 'Caregivers 6-23m',
                    'hasCustomLabel': True
                }
            ],
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 10000,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'top',
            'rich_tooltip': True,
            'y_axis_format': ',.0f',
            'truncateXAxis': True
        })
    ))

    # Area Chart: Education Sessions Trend
    charts.append(Slice(
        slice_name='Education Sessions Trend',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_area',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_area',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(edu_session_1st_visit)',
                    'label': '1st Visit',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(edu_session_gt1_visit)',
                    'label': 'Follow-up Visits',
                    'hasCustomLabel': True
                }
            ],
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 10000,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'top',
            'rich_tooltip': True,
            'y_axis_format': ',.0f',
            'opacity': 0.5,
            'truncateXAxis': True
        })
    ))

    # Save all charts
    for chart in charts:
        db.session.add(chart)
    db.session.commit()

    # Add charts to dashboard
    dashboard.slices.extend(charts)
    db.session.commit()

    print(f"✓ Created {len(charts)} charts:")
    for i, chart in enumerate(charts, 1):
        print(f"  {i}. {chart.slice_name} ({chart.viz_type})")

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print(f"\nDashboard URL: http://localhost:8088/superset/dashboard/{DASHBOARD_SLUG}/")
    print(f"Dataset ID: {dataset.id}")
    print(f"Dashboard ID: {dashboard.id}")
    print()
