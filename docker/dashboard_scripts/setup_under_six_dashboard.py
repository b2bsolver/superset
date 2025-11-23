#!/usr/bin/env python3
"""
Under Six Monthly Reports Dashboard Setup
Creates dataset and dashboard with all charts from scratch
Run: docker exec superset_app python /app/docker/dashboard_scripts/setup_under_six_dashboard.py
"""
import sys
import json
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Configuration
TABLE_NAME = 'under_six_monthly_reports'
DASHBOARD_TITLE = 'Under Six Monthly Dashboard'
DASHBOARD_SLUG = 'under-six-monthly-dashboard'
DATABASE_NAME = 'MySQL'

with app.app_context():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("=" * 80)
    print(f"UNDER SIX MONTHLY REPORTS DASHBOARD SETUP")
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
        print(f"  ✓ Cleared existing charts")
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

    # Big Number 1: Total RAPID Cases
    charts.append(Slice(
        slice_name='Total RAPID Cases',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(rapid)',
                'label': 'Total RAPID',
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

    # Big Number 2: Inpatient Referrals
    charts.append(Slice(
        slice_name='Inpatient Referrals',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(referred_inpatient_services)',
                'label': 'Inpatient Referrals',
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

    # Big Number 3: Total Referrals
    charts.append(Slice(
        slice_name='Total Referrals',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(referral_any_indepth_assessment)',
                'label': 'Total Referrals',
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

    # Big Number 4: Reduced Visit Frequency
    charts.append(Slice(
        slice_name='Reduced Visit Frequency',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(reduced_visit_frequency_yes)',
                'label': 'Reduced Visits',
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

    # Line Chart: Monthly Capacity Training
    charts.append(Slice(
        slice_name='Monthly Capacity Training',
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
                    'sqlExpression': 'SUM(capacity_trained_reporting_month)',
                    'label': 'This Month',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(capacity_trained_till_reporting_month)',
                    'label': 'Cumulative',
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
            'markerSize': 6,
            'truncateXAxis': True,
            'x_axis_time_format': 'smart_date'
        })
    ))

    # Bar Chart: Referral Services
    charts.append(Slice(
        slice_name='Referral Services Breakdown',
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
                    'sqlExpression': 'SUM(referral_indepth_iycf_yes)',
                    'label': 'IYCF',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(referral_indepth_pss_yes)',
                    'label': 'PSS',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(referral_both_pss_iycf_yes)',
                    'label': 'Both PSS & IYCF',
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

    # Bar Chart: Services After 6 Months
    charts.append(Slice(
        slice_name='Services After 6 Months',
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
                    'sqlExpression': 'SUM(service_availed_after_6months_otp)',
                    'label': 'OTP',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(service_availed_after_6months_tsfp)',
                    'label': 'TSFP',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(service_availed_after_6months_bsfp)',
                    'label': 'BSFP',
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

    # Area Chart: Higher PSS Referrals Trend
    charts.append(Slice(
        slice_name='Higher PSS Referrals Trend',
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
                    'sqlExpression': 'SUM(referral_higher_pss_yes_with_pss_reg_no)',
                    'label': 'Higher PSS Referrals',
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
