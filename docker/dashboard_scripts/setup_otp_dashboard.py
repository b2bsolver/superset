#!/usr/bin/env python3
"""
OTP Reports Dashboard Setup
Creates dataset and dashboard with all charts from scratch
Run: docker compose exec superset python /app/docker/dashboard_scripts/setup_otp_dashboard.py
"""
import sys
import json
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Configuration
TABLE_NAME = 'otp_reports'
DASHBOARD_TITLE = 'OTP Dashboard'
DASHBOARD_SLUG = 'otp-dashboard'


def select_database(db):
    """Select database - auto-select if single, prompt if multiple"""
    from superset.models.core import Database

    all_databases = db.session.query(Database).all()

    if not all_databases:
        print("✗ No databases found! Please configure a database connection first.")
        sys.exit(1)

    if len(all_databases) == 1:
        database = all_databases[0]
        print(f"✓ Using database '{database.database_name}' (ID: {database.id})")
        return database

    # Multiple databases - let user choose
    print(f"\nFound {len(all_databases)} databases:")
    for idx, db_item in enumerate(all_databases, 1):
        print(f"  {idx}. {db_item.database_name} (ID: {db_item.id})")

    while True:
        choice = input(f"\nSelect database [1-{len(all_databases)}]: ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(all_databases):
                database = all_databases[idx - 1]
                print(f"✓ Selected '{database.database_name}'")
                return database
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(all_databases)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


with app.app_context():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("=" * 80)
    print(f"OTP REPORTS DASHBOARD SETUP")
    print("=" * 80)

    # Step 1: Get Database
    print("\n[1/4] Selecting Database...")
    database = select_database(db)

    # Step 2: Create/Update OTP Dataset
    print(f"\n[2/5] Setting up OTP Dataset...")
    dataset = db.session.query(SqlaTable).filter_by(
        database_id=database.id,
        table_name=TABLE_NAME
    ).first()

    # SQL query to join with infs table for latitude/longitude and camps for boundaries
    # Note: otp_reports already has program_partner, implementing_partner, camp_site
    # Convert boundary_geom JSON to proper GeoJSON string for deck.gl
    dataset_sql = """
        SELECT
            otp.*,
            infs.latitude,
            infs.longitude,
            infs.title as inf_title,
            CASE
                WHEN camps.boundary_geom IS NOT NULL
                THEN JSON_UNQUOTE(JSON_EXTRACT(CONCAT('{"type":"Feature","geometry":', camps.boundary_geom, ',"properties":{}}'), '$'))
                ELSE NULL
            END as boundary_geom
        FROM otp_reports as otp
        LEFT JOIN infs ON otp.inf_id = infs.id
        LEFT JOIN camps ON otp.camp_site = camps.title
    """

    if dataset:
        print(f"  ℹ Dataset '{TABLE_NAME}' already exists (ID: {dataset.id})")
        # Update SQL query
        dataset.sql = dataset_sql
        # Refresh metadata
        dataset.fetch_metadata()
        db.session.commit()
        print(f"  ✓ Refreshed dataset metadata with JOIN to infs and camps tables")
    else:
        dataset = SqlaTable(
            table_name=TABLE_NAME,
            database=database,
            schema='',
            sql=dataset_sql
        )
        db.session.add(dataset)
        db.session.commit()
        dataset.fetch_metadata()
        db.session.commit()
        print(f"✓ Created dataset '{TABLE_NAME}' (ID: {dataset.id}) with JOIN to infs and camps tables")

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

    # ========== Big Number Cards ==========

    # Big Number 1: New Enrolment
    charts.append(Slice(
        slice_name='New Enrolment',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(enrolment_only_muac+enrolment_only_wfh+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                'label': 'Enrolment',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.4,
            'subheader_font_size': 0.15,
            'y_axis_format': ',d'
        })
    ))

    # Big Number 2: Transfer In
    charts.append(Slice(
        slice_name='Transfer In',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(transfer_in_from_sc+transfer_from_tsfp+transfer_other_otp)',
                'label': 'Transfer In',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.4,
            'subheader_font_size': 0.15,
            'y_axis_format': ',d'
        })
    ))

    # Big Number 3: Discharge
    charts.append(Slice(
        slice_name='Discharge',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(recovered+death+defaulted+non_recovered)',
                'label': 'Discharge',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.4,
            'subheader_font_size': 0.15,
            'y_axis_format': ',d'
        })
    ))

    # Big Number 4: Transfer Out
    charts.append(Slice(
        slice_name='Transfer Out',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(transfer_to_other_otp+transfer_inpatient+medical_transfer)',
                'label': 'Transfer Out',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.4,
            'subheader_font_size': 0.15,
            'y_axis_format': ',d'
        })
    ))

    # Big Number 5: Recovery Rate
    charts.append(Slice(
        slice_name='Recovery Rate',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(recovered)/SUM(recovered+death+defaulted+non_recovered)',
                'label': 'Recovery Rate',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.4,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.1%'
        })
    ))

    # ========== Line Charts ==========

    # Line Chart: Monthly Enrollment
    charts.append(Slice(
        slice_name='Monthly Enrollment',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_line',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_line',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', month)'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                    'label': 'Enrolment',
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

    # Line Chart: Recovery Rate Trend
    charts.append(Slice(
        slice_name='Recovery Rate Trend',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_line',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_line',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', month)'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                    'label': 'Recovery Rate %',
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

    # Smooth Line Chart: Beneficiary In Care
    charts.append(Slice(
        slice_name='Beneficiary In Care',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_smooth',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_smooth',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \'-\', month)'
            },
            'metrics': [
                {
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'total_in_care_end_month'},
                    'aggregate': 'SUM',
                    'label': 'In Care',
                    'hasCustomLabel': True
                }
            ],
            'groupby': ['implementing_partner'],
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 50000,
            'color_scheme': 'supersetAndPresetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'bottom',
            'rich_tooltip': True,
            'y_axis_format': '~g',
            'truncateXAxis': True,
            'x_axis_time_format': 'smart_date'
        })
    ))

    # ========== Bar Charts ==========

    # Bar Chart: Performance Analysis (Stacked)
    charts.append(Slice(
        slice_name='Performance Analysis',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month Year',
                'sqlExpression': 'CONCAT(year, \' -\', month)'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)* 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                    'label': 'Recovered',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(death)* 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                    'label': 'Death',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(defaulted) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                    'label': 'Defaulted',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(non_recovered) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                    'label': 'Non Recovered',
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
            'row_limit': 5000,
            'color_scheme': 'supersetAndPresetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'bottom',
            'rich_tooltip': True,
            'y_axis_format': ',.1f',
            'stack': 'Stack',
            'truncateXAxis': True,
            'y_axis_bounds': [0, 100]
        })
    ))

    # Bar Chart: Care Given
    charts.append(Slice(
        slice_name='Care Given',
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
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'total_in_care_end_month'},
                    'aggregate': 'SUM',
                    'label': 'Care Given',
                    'hasCustomLabel': True
                }
            ],
            'groupby': ['age_group'],
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

    # Bar Chart: OTP Caseload Distribution by Location
    charts.append(Slice(
        slice_name='OTP Caseload Distribution by Location',
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
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'total_in_care_end_month'},
                    'aggregate': 'SUM',
                    'label': 'Caseload',
                    'hasCustomLabel': True
                }
            ],
            'groupby': ['program_partner'],
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

    # ========== Sunburst Chart ==========

    # Sunburst: Hierarchical Beneficiary Distribution
    charts.append(Slice(
        slice_name='Beneficiary Hierarchy (Camp > Partner)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='sunburst_v2',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'sunburst_v2',
            'columns': ['camp_site', 'implementing_partner'],
            'metric': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM',
                'label': 'Beneficiaries',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 1000,
            'color_scheme': 'supersetColors',
            'linear_color_scheme': 'schemeRdYlBu'
        })
    ))

    # ========== Treemap Chart ==========

    # Treemap: Recovery Status Distribution
    charts.append(Slice(
        slice_name='Discharge Outcomes Treemap',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='treemap_v2',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'treemap_v2',
            'groupby': ['camp_site'],
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)',
                    'label': 'Recovered',
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
            'row_limit': 100,
            'color_scheme': 'bnbColors',
            'number_format': ',.0f'
        })
    ))

    # ========== Mixed Time Series Chart ==========

    # Mixed Chart: Enrollment vs Recovery (Bar + Line)
    charts.append(Slice(
        slice_name='Enrollment vs Recovery Trend',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='mixed_timeseries',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'mixed_timeseries',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                    'label': 'New Enrollment',
                    'hasCustomLabel': True
                }
            ],
            'metrics_b': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)',
                    'label': 'Recovered',
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
            'legendOrientation': 'top',
            'y_axis_format': ',.0f',
            'y_axis_format_secondary': ',.0f',
            'truncateXAxis': True
        })
    ))

    # ========== Gauge Chart ==========

    # Gauge: Overall Recovery Rate Performance
    charts.append(Slice(
        slice_name='Recovery Rate Gauge',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='gauge_chart',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'gauge_chart',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': '(SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0))',
                'label': 'Recovery Rate %',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 10000,
            'min_val': 0,
            'max_val': 100,
            'start_angle': 225,
            'end_angle': -45,
            'color_scheme': 'supersetColors',
            'font_size': 15,
            'number_format': '.1f',
            'value_formatter': '{value}%',
            'show_pointer': True,
            'animation': True,
            'show_axis_tick': True,
            'show_split_line': True,
            'split_number': 10,
            'show_progress': True,
            'overlap': True,
            'round_cap': True
        })
    ))

    # ========== Radar Chart ==========

    # Radar: Multi-dimensional Performance by Partner
    charts.append(Slice(
        slice_name='Partner Performance Radar',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='radar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'radar',
            'groupby': ['implementing_partner'],
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                    'label': 'Enrollment',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)',
                    'label': 'Recovered',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(total_in_care_end_month)',
                    'label': 'In Care',
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
            'row_limit': 50,
            'color_scheme': 'supersetColors',
            'label_type': 'key',
            'show_legend': True,
            'legendOrientation': 'top'
        })
    ))

    # ========== Stacked Area Chart (Beneficiary Flow) ==========

    # Area Chart: Beneficiary Flow Over Time
    charts.append(Slice(
        slice_name='Beneficiary Flow Over Time',
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
                    'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                    'label': 'Enrollment',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(transfer_in_from_sc+transfer_from_tsfp+transfer_other_otp)',
                    'label': 'Transfer In',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(total_in_care_end_month)',
                    'label': 'In Care',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)',
                    'label': 'Recovered',
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
            'opacity': 0.7,
            'stack': 'Stream',
            'truncateXAxis': True
        })
    ))

    # ========== Bubble Chart ==========

    # Bubble: Partner Performance Matrix
    charts.append(Slice(
        slice_name='Partner Performance Matrix (Bubble)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='bubble',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'bubble',
            'series': 'implementing_partner',
            'entity': 'camp_site',
            'x': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                'label': 'Enrollment',
                'hasCustomLabel': True
            },
            'y': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0)',
                'label': 'Recovery Rate %',
                'hasCustomLabel': True
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM',
                'label': 'Beneficiaries in Care',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 1000,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'max_bubble_size': 50,
            'x_axis_format': ',.0f',
            'y_axis_format': '.1f'
        })
    ))

    # ========== Bar Chart (Journey Stages) ==========

    # Bar Chart: OTP Journey Stages Summary
    charts.append(Slice(
        slice_name='OTP Journey Stages',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Stage',
                'sqlExpression': 'camp_site'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(enrolment_only_wfh+enrolment_only_muac+enrolment_both_muac_wfh+enrolment_edema+enrolment_relapse)',
                    'label': 'Enrollment',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(total_in_care_end_month)',
                    'label': 'In Care',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered)',
                    'label': 'Recovered',
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

    # ========== Bar Chart (Recovery Rate by Camp) ==========

    # Bar Chart: Recovery Rate by Camp
    charts.append(Slice(
        slice_name='Recovery Rate by Camp',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Camp',
                'sqlExpression': 'camp_site'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': '(SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + defaulted + non_recovered), 0))',
                    'label': 'Recovery Rate %',
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
            'y_axis_format': '.1f',
            'truncateXAxis': True,
            'y_axis_bounds': [0, 100]
        })
    ))

    # ========== Pie Charts ==========

    # Pie Chart: Beneficiary Distribution by Camp
    charts.append(Slice(
        slice_name='Beneficiary Distribution by Camp',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='pie',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'pie',
            'groupby': ['camp_site'],
            'metric': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM',
                'label': 'Beneficiaries in Care',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 100,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'right',
            'label_type': 'key_value',
            'number_format': ',.0f',
            'show_labels_threshold': 5,
            'donut': False,
            'innerRadius': 30,
            'outerRadius': 70
        })
    ))

    # Pie Chart: Beneficiary Distribution by Partner
    charts.append(Slice(
        slice_name='Beneficiary Distribution by Partner',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='pie',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'pie',
            'groupby': ['implementing_partner'],
            'metric': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM',
                'label': 'Beneficiaries in Care',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'row_limit': 100,
            'color_scheme': 'supersetColors',
            'show_legend': True,
            'legendType': 'scroll',
            'legendOrientation': 'right',
            'label_type': 'key_value',
            'number_format': ',.0f',
            'show_labels_threshold': 5,
            'donut': False,
            'innerRadius': 30,
            'outerRadius': 70
        })
    ))

    # ========== Geographic Visualizations ==========

    # Map 1: Hexagon Layer - 3D Beneficiary Density (Dark Style)
    charts.append(Slice(
        slice_name='3D Beneficiary Density (Hexagon)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_hex',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_hex',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/dark-v10',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11,
                'pitch': 40,
                'bearing': 0
            },
            'grid_size': 40,
            'extruded': True,
            'color_picker': {'r': 14, 'g': 77, 'b': 146, 'a': 1},
            'linear_color_scheme': 'blue_white_yellow',
            'js_columns': [],
            'js_data_mutator': '',
            'js_tooltip': '',
            'js_onclick_href': ''
        })
    ))

    # Map 2: Screengrid - High Intensity Heatmap (Streets Style)
    charts.append(Slice(
        slice_name='Beneficiary Intensity Heatmap',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_screengrid',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_screengrid',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/streets-v11',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11,
                'pitch': 0,
                'bearing': 0
            },
            'grid_size': 20,
            'linear_color_scheme': 'oranges',
            'opacity': 80
        })
    ))

    # Map 3: Contour - Geographic Coverage Zones (Satellite Style)
    charts.append(Slice(
        slice_name='Coverage Zones (Contour)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_contour',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_contour',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/satellite-streets-v11',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11,
                'pitch': 0,
                'bearing': 0
            },
            'linear_color_scheme': 'purples',
            'contours': [
                {'threshold': 10, 'color': [255, 255, 178], 'strokeWidth': 1},
                {'threshold': 50, 'color': [254, 204, 92], 'strokeWidth': 1},
                {'threshold': 100, 'color': [253, 141, 60], 'strokeWidth': 2},
                {'threshold': 200, 'color': [227, 26, 28], 'strokeWidth': 2}
            ],
            'cell_size': 200,
            'aggregation': 'SUM'
        })
    ))

    # Map 4: Scatter with Variable Sizes - Camp Activity Bubbles (Outdoors Style)
    charts.append(Slice(
        slice_name='Camp Activity Bubbles',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_scatter',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_scatter',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/outdoors-v11',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11,
                'pitch': 0,
                'bearing': 0
            },
            'point_radius_fixed': {
                'type': 'metric'
            },
            'point_radius_scale': 1,
            'point_unit': 'pixels',
            'filled': True,
            'stroked': True,
            'color_picker': {'r': 76, 'g': 175, 'b': 80, 'a': 0.8}
        })
    ))

    # Map 5: Grid - Square Grid Density (Navigation Style)
    charts.append(Slice(
        slice_name='Grid Density Map',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_grid',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_grid',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'size': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/navigation-day-v1',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11,
                'pitch': 45,
                'bearing': 0
            },
            'grid_size': 50,
            'extruded': True,
            'linear_color_scheme': 'greens',
            'opacity': 80
        })
    ))

    # Map 6: Heatmap - Classic Density Heatmap
    charts.append(Slice(
        slice_name='Beneficiary Care Heatmap',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_heatmap',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_heatmap',
            'spatial': {
                'type': 'latlong',
                'latCol': 'latitude',
                'lonCol': 'longitude'
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'latitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'subject': 'longitude',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 50000,
            'mapbox_style': 'mapbox://styles/mapbox/light-v10',
            'viewport': {
                'latitude': 21.4,
                'longitude': 92.0,
                'zoom': 11
            },
            'linear_color_scheme': 'reds',
            'intensity': 1,
            'radius_pixels': 60,
            'aggregation': 'SUM'
        })
    ))

    # Map 7: Camp Boundaries (Light Theme) - Using GeoJSON
    charts.append(Slice(
        slice_name='Camp Boundaries Map',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_geojson',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_geojson',
            'geojson': 'boundary_geom',
            'groupby': ['camp_site'],
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'boundary_geom',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 5000,
            'mapbox_style': 'mapbox://styles/mapbox/light-v10',
            'viewport': {
                'longitude': 92.15,
                'latitude': 21.2,
                'zoom': 12,
                'pitch': 0,
                'bearing': 0
            },
            'fill_color_picker': {'r': 76, 'g': 175, 'b': 80, 'a': 0.4},
            'stroke_color_picker': {'r': 255, 'g': 87, 'b': 34, 'a': 0.9},
            'filled': True,
            'stroked': True,
            'extruded': False,
            'line_width_min_pixels': 3,
            'point_radius_scale': 1
        })
    ))

    # Map 8: Camp Boundaries (Satellite View)
    charts.append(Slice(
        slice_name='Camp Boundaries - Satellite',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_geojson',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_geojson',
            'geojson': 'boundary_geom',
            'groupby': ['camp_site'],
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'boundary_geom',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 5000,
            'mapbox_style': 'mapbox://styles/mapbox/satellite-streets-v11',
            'viewport': {
                'longitude': 92.15,
                'latitude': 21.2,
                'zoom': 13,
                'pitch': 0,
                'bearing': 0
            },
            'fill_color_picker': {'r': 255, 'g': 235, 'b': 59, 'a': 0.25},
            'stroke_color_picker': {'r': 255, 'g': 87, 'b': 34, 'a': 1},
            'filled': True,
            'stroked': True,
            'extruded': False,
            'line_width_min_pixels': 3,
            'point_radius_scale': 1
        })
    ))

    # Map 9: 3D Camp Boundaries (Dark Theme)
    charts.append(Slice(
        slice_name='3D Camp Boundaries',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_geojson',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_geojson',
            'geojson': 'boundary_geom',
            'groupby': ['camp_site'],
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'boundary_geom',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 5000,
            'mapbox_style': 'mapbox://styles/mapbox/dark-v10',
            'viewport': {
                'longitude': 92.15,
                'latitude': 21.2,
                'zoom': 12,
                'pitch': 60,
                'bearing': 30
            },
            'fill_color_picker': {'r': 33, 'g': 150, 'b': 243, 'a': 0.6},
            'stroke_color_picker': {'r': 0, 'g': 229, 'b': 255, 'a': 1},
            'filled': True,
            'stroked': True,
            'extruded': True,
            'point_radius_scale': 100,
            'line_width_min_pixels': 2
        })
    ))

    # Map 10: Choropleth - Beneficiary Count by Camp Boundary
    charts.append(Slice(
        slice_name='Beneficiary Choropleth (Camp Boundaries)',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='deck_geojson',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'deck_geojson',
            'geojson': 'boundary_geom',
            'groupby': ['camp_site'],
            'metric': {
                'expressionType': 'SIMPLE',
                'column': {'column_name': 'total_in_care_end_month'},
                'aggregate': 'SUM',
                'label': 'Beneficiaries',
                'hasCustomLabel': True
            },
            'adhoc_filters': [
                {
                    'clause': 'WHERE',
                    'subject': 'boundary_geom',
                    'operator': 'IS NOT NULL',
                    'comparator': '',
                    'expressionType': 'SIMPLE'
                },
                {
                    'clause': 'WHERE',
                    'comparator': 'No filter',
                    'expressionType': 'SIMPLE',
                    'operator': 'TEMPORAL_RANGE',
                    'subject': 'created_at'
                }
            ],
            'row_limit': 5000,
            'mapbox_style': 'mapbox://styles/mapbox/light-v10',
            'viewport': {
                'longitude': 92.15,
                'latitude': 21.2,
                'zoom': 12,
                'pitch': 0,
                'bearing': 0
            },
            'linear_color_scheme': 'blue_white_yellow',
            'filled': True,
            'stroked': True,
            'extruded': False,
            'line_width_min_pixels': 2,
            'opacity': 70
        })
    ))

    # Save all charts
    for chart in charts:
        db.session.add(chart)
    db.session.commit()

    # Add charts to dashboard
    dashboard.slices.extend(charts)

    # Commit to ensure chart IDs are assigned
    db.session.commit()

    # Get all chart IDs (filter out None values)
    chart_ids = [chart.id for chart in charts if chart.id is not None]

    # Configure native filters with NULL exclusion
    native_filters = [
        {
            'id': 'NATIVE_FILTER-year',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Year',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'year'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        },
        {
            'id': 'NATIVE_FILTER-month',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Month',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'month'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        },
        {
            'id': 'NATIVE_FILTER-gender',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Gender',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'gender'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        },
        {
            'id': 'NATIVE_FILTER-age-group',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Age Group',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'age_group'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        },
        {
            'id': 'NATIVE_FILTER-program-partner',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Program Partner',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'program_partner'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        },
        {
            'id': 'NATIVE_FILTER-implementing-partner',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Implementing Partner',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'implementing_partner'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': [],
            'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'type': 'NATIVE_FILTER',
            'description': '',
            'chartsInScope': chart_ids,
            'tabsInScope': []
        }
    ]

    # Update dashboard metadata with native filters and cross-filtering
    dashboard.json_metadata = json.dumps({
        'color_scheme': '',
        'refresh_frequency': 0,
        'expanded_slices': {},
        'label_colors': {},
        'timed_refresh_immune_slices': [],
        'cross_filters_enabled': True,
        'default_filters': '{}',
        'native_filter_configuration': native_filters
    })

    db.session.commit()

    print(f"✓ Created {len(charts)} charts:")
    for i, chart in enumerate(charts, 1):
        print(f"  {i}. {chart.slice_name} ({chart.viz_type})")

    # Update filter count
    filter_names = [f['name'] for f in native_filters]

    print(f"✓ Configured {len(native_filters)} native filters:")
    print(f"  - {', '.join(filter_names)}")

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print(f"\nDashboard URL: http://localhost:8088/superset/dashboard/{DASHBOARD_SLUG}/")
    print(f"Dataset ID: {dataset.id}")
    print(f"Dashboard ID: {dashboard.id}")
    print(f"Dataset UUID: {dataset.uuid}")
    print()
