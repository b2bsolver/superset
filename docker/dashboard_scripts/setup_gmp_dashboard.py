#!/usr/bin/env python3
"""
GMP Report Archives Dashboard Setup
Creates dataset and dashboard with all charts from scratch
Run: docker compose exec superset python /app/docker/dashboard_scripts/setup_gmp_dashboard.py
"""
import sys
import json
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Configuration
TABLE_NAME = 'gmp_report_archives'
DASHBOARD_TITLE = 'GMP Report Archives Dashboard'
DASHBOARD_SLUG = 'gmp-report-archives-dashboard'


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
    print(f"GMP REPORT ARCHIVES DASHBOARD SETUP")
    print("=" * 80)

    # Step 1: Get Database
    print("\n[1/4] Selecting Database...")
    database = select_database(db)

    # Step 2: Create/Update Dataset
    print(f"\n[2/4] Setting up Dataset...")
    dataset = db.session.query(SqlaTable).filter_by(
        database_id=database.id,
        table_name=TABLE_NAME
    ).first()

    # SQL query to enrich GMP data with INF location + partner metadata
    dataset_sql = """
        SELECT
            gmp.*,
            infs.latitude,
            infs.longitude,
            infs.title as inf_title,
            infs.facility_code,
            camps.title as camp_site,
            program_partners.program_partner,
            implementing_partners.implementing_partner
        FROM gmp_report_archives as gmp
        LEFT JOIN infs ON gmp.inf_id = infs.id
        LEFT JOIN camps ON infs.camp_id = camps.id
        LEFT JOIN (
            SELECT
                inf_pps.inf_id,
                GROUP_CONCAT(DISTINCT pps.title ORDER BY pps.title SEPARATOR ', ') AS program_partner
            FROM inf_pps
            JOIN pps ON inf_pps.pp_id = pps.id
            GROUP BY inf_pps.inf_id
        ) AS program_partners ON gmp.inf_id = program_partners.inf_id
        LEFT JOIN (
            SELECT
                inf_ips.inf_id,
                GROUP_CONCAT(DISTINCT ips.title ORDER BY ips.title SEPARATOR ', ') AS implementing_partner
            FROM inf_ips
            JOIN ips ON inf_ips.ip_id = ips.id
            GROUP BY inf_ips.inf_id
        ) AS implementing_partners ON gmp.inf_id = implementing_partners.inf_id
    """

    if dataset:
        print(f"  ℹ Dataset '{TABLE_NAME}' already exists (ID: {dataset.id})")
        # Update SQL query
        dataset.sql = dataset_sql
        # Refresh metadata
        dataset.fetch_metadata()
        db.session.commit()
        print(f"  ✓ Refreshed dataset metadata with JOIN to infs table")
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
        print(f"✓ Created dataset '{TABLE_NAME}' (ID: {dataset.id}) with JOIN to infs table")

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

    # Big Number 1: Total Target Children
    charts.append(Slice(
        slice_name='Total Target Children',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(target_total_t)',
                'label': 'Target Total',
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

    # Big Number 2: Total Screened
    charts.append(Slice(
        slice_name='Total Screened',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(done_total_t)',
                'label': 'Screened Total',
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

    # Big Number 3: Achievement Rate
    charts.append(Slice(
        slice_name='Achievement Rate',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'AVG(ach_t)',
                'label': 'Achievement %',
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
            'y_axis_format': ',.1f'
        })
    ))

    # Big Number 4: Total SAM Cases
    charts.append(Slice(
        slice_name='Total SAM Cases',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(sam_total_t)',
                'label': 'SAM Total',
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

    # Big Number 5: Total MAM Cases
    charts.append(Slice(
        slice_name='Total MAM Cases',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(mam_total_t)',
                'label': 'MAM Total',
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

    # Big Number 6: Total OTP Referrals
    charts.append(Slice(
        slice_name='Total OTP Referrals',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(refer_otp_t)',
                'label': 'OTP Referrals',
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

    # ========== Line Charts ==========

    # Line Chart: Monthly Screening Trend
    charts.append(Slice(
        slice_name='Monthly Screening Trend',
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
                    'sqlExpression': 'SUM(target_total_t)',
                    'label': 'Target',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(done_total_t)',
                    'label': 'Screened',
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

    # Line Chart: Malnutrition Trend
    charts.append(Slice(
        slice_name='Malnutrition Cases Trend',
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
                    'sqlExpression': 'SUM(sam_total_t)',
                    'label': 'SAM',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(mam_total_t)',
                    'label': 'MAM',
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

    # ========== Bar Charts ==========

    # Bar Chart: Target vs Achievement by Age Group
    charts.append(Slice(
        slice_name='Screening by Age Group',
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
                    'sqlExpression': 'SUM(done_0_5_t)',
                    'label': '0-5 months',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(done_6_23_t)',
                    'label': '6-23 months',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(done_24_59_t)',
                    'label': '24-59 months',
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

    # Bar Chart: Gender Distribution
    charts.append(Slice(
        slice_name='Screening by Gender',
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
                    'sqlExpression': 'SUM(done_total_m)',
                    'label': 'Male',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(done_total_f)',
                    'label': 'Female',
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

    # Bar Chart: Growth Status
    charts.append(Slice(
        slice_name='Growth Status Distribution',
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
                    'sqlExpression': 'SUM(growth_positive_t)',
                    'label': 'Positive',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(growth_static_t)',
                    'label': 'Static',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(growth_faltered_t)',
                    'label': 'Faltered',
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

    # Bar Chart: SAM Detection Methods
    charts.append(Slice(
        slice_name='SAM Detection Methods',
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
                    'sqlExpression': 'SUM(sam_muac_t)',
                    'label': 'MUAC',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(sam_whz_t)',
                    'label': 'WHZ',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(sam_both_t)',
                    'label': 'Both',
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

    # Bar Chart: MAM by Method
    charts.append(Slice(
        slice_name='MAM Detection Methods',
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
                    'sqlExpression': 'SUM(mam_muac_t)',
                    'label': 'MUAC',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(mam_whz_t)',
                    'label': 'WHZ',
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

    # Bar Chart: Referrals
    charts.append(Slice(
        slice_name='Referrals by Program',
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
                    'sqlExpression': 'SUM(refer_otp_t)',
                    'label': 'OTP',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(refer_tsfp_t)',
                    'label': 'TSFP',
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

    # Bar Chart: Other Nutrition Indicators
    charts.append(Slice(
        slice_name='Other Nutrition Indicators',
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
                    'sqlExpression': 'SUM(stunting_t)',
                    'label': 'Stunting',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(underweight_t)',
                    'label': 'Underweight',
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

    # ========== Area Charts ==========

    # Area Chart: Cumulative Screening
    charts.append(Slice(
        slice_name='Cumulative Screening Trend',
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
                    'sqlExpression': 'SUM(done_total_t)',
                    'label': 'Total Screened',
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

    # Area Chart: Growth Faltering Trend
    charts.append(Slice(
        slice_name='Growth Faltering Trend',
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
                    'sqlExpression': 'SUM(growth_faltered_t)',
                    'label': 'Growth Faltered',
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

    # Get all chart IDs
    chart_ids = [chart.id for chart in charts]

    # Configure native filters
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
        },
        {
            'id': 'NATIVE_FILTER-camp-site',
            'controlValues': {
                'enableEmptyFilter': False,
                'defaultToFirstItem': False,
                'multiSelect': True,
                'searchAllOptions': False,
                'inverseSelection': False
            },
            'name': 'Camp Site',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'camp_site'},
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

    # Update dashboard metadata with native filters
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

    print(f"✓ Configured {len(native_filters)} native filters:")
    print(f"  - Year, Month, Program Partner, Implementing Partner, Camp Site")

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print(f"\nDashboard URL: http://localhost:8088/superset/dashboard/{DASHBOARD_SLUG}/")
    print(f"Dataset ID: {dataset.id}")
    print(f"Dashboard ID: {dashboard.id}")
    print(f"Dataset UUID: {dataset.uuid}")
    print()
