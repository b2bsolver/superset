#!/usr/bin/env python3
"""
SC (Stabilization Center) Reports Dashboard Setup
Creates dataset and dashboard with all charts from scratch
Run: docker compose exec superset python /app/docker/dashboard_scripts/setup_sc_dashboard.py
"""
import sys
import json
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()

# Configuration
TABLE_NAME = 'sc_reports'
DASHBOARD_TITLE = 'SC Dashboard'
DASHBOARD_SLUG = 'sc-dashboard'


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
    print(f"SC REPORTS DASHBOARD SETUP")
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

    # SQL query to join with infs table for latitude/longitude
    # Note: sc_reports already has program_partner, implementing_partner, camp_site
    dataset_sql = """
        SELECT
            sc.*,
            infs.latitude,
            infs.longitude,
            infs.title as inf_title
        FROM sc_reports as sc
        LEFT JOIN infs ON sc.inf_id = infs.id
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

    # Big Number 1: Success Rate (Recovered + Transfer to OTP)
    charts.append(Slice(
        slice_name='Success Rate',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(recovered + transfer_to_otp) / SUM(recovered + transfer_to_otp + death + non_responder + defaulted + exit_others)',
                'label': 'Success Rate',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.6,
            'subheader_font_size': 0.15,
            'y_axis_format': ',.1%'
        })
    ))

    # Big Number 2: New Admission
    charts.append(Slice(
        slice_name='New Admission',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(new_wh_lt_3sd+new_muac_lt_115+new_both+new_edema+new_relapse)',
                'label': 'New Admission',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.6,
            'subheader_font_size': 0.2,
            'y_axis_format': '~g'
        })
    ))

    # Big Number 3: Transfer In
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
                'sqlExpression': 'SUM(transfer_in_from_otp+readmission_after_default)',
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
            'header_font_size': 0.6,
            'subheader_font_size': 0.2,
            'y_axis_format': '~g'
        })
    ))

    # Big Number 4: Discharge
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
                'sqlExpression': 'SUM(recovered+death+non_responder)',
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
            'header_font_size': 0.6,
            'subheader_font_size': 0.2,
            'y_axis_format': '~g'
        })
    ))

    # Big Number 5: Other Exit
    charts.append(Slice(
        slice_name='Other Exit',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(exit_others+defaulted)',
                'label': 'Other Exit',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.6,
            'subheader_font_size': 0.2,
            'y_axis_format': '~g'
        })
    ))

    # Big Number 6: Total Exit
    charts.append(Slice(
        slice_name='Total Exit',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='big_number_total',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'big_number_total',
            'metric': {
                'expressionType': 'SQL',
                'sqlExpression': 'SUM(recovered+death+non_responder+defaulted+exit_others+transfer_to_otp+medical_transfer)',
                'label': 'Total Exit',
                'hasCustomLabel': True
            },
            'adhoc_filters': [{
                'clause': 'WHERE',
                'comparator': 'No filter',
                'expressionType': 'SIMPLE',
                'operator': 'TEMPORAL_RANGE',
                'subject': 'created_at'
            }],
            'header_font_size': 0.6,
            'subheader_font_size': 0.2,
            'y_axis_format': '~g'
        })
    ))

    # ========== Smooth Line Charts ==========

    # Smooth Line Chart: SC Admission Trend
    charts.append(Slice(
        slice_name='SC Admission Trend',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_smooth',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_smooth',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(new_wh_lt_3sd+new_muac_lt_115+new_both+new_edema+new_relapse)',
                    'label': 'New Admission',
                    'hasCustomLabel': True
                }
            ],
            'groupby': ['gender'],
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
            'y_axis_format': 'SMART_NUMBER',
            'markerEnabled': True,
            'markerSize': 3,
            'truncateXAxis': True
        })
    ))

    # ========== Bar Charts ==========

    # Bar Chart: Recovered Trend
    charts.append(Slice(
        slice_name='Recovered',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'recovered'},
                    'aggregate': 'SUM',
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

    # Bar Chart: OTP Transfer
    charts.append(Slice(
        slice_name='OTP Transfer',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'transfer_to_otp'},
                    'aggregate': 'SUM',
                    'label': 'OTP Transfer',
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

    # Bar Chart: Medical Transfer
    charts.append(Slice(
        slice_name='Medical Transfer',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'medical_transfer'},
                    'aggregate': 'SUM',
                    'label': 'Medical Transfer',
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

    # Bar Chart: Defaulted
    charts.append(Slice(
        slice_name='Defaulted',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SIMPLE',
                    'column': {'column_name': 'defaulted'},
                    'aggregate': 'SUM',
                    'label': 'Defaulted',
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

    # Bar Chart: Camp wise Performance Analysis (Stacked)
    charts.append(Slice(
        slice_name='Camp wise Performance Analysis',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Camp Site',
                'sqlExpression': 'camp_site'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Recovered %',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(transfer_to_otp) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'OTP Transfer %',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(death) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Death %',
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
            'legendOrientation': 'bottom',
            'rich_tooltip': True,
            'y_axis_format': ',.1f',
            'stack': 'Stack',
            'truncateXAxis': True,
            'y_axis_bounds': [0, 100]
        })
    ))

    # Bar Chart: Age Group Performance
    charts.append(Slice(
        slice_name='Age Group Performance',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(new_wh_lt_3sd+new_muac_lt_115+new_both+new_edema+new_relapse)',
                    'label': 'Admissions',
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

    # Bar Chart: Gender Wise Admission
    charts.append(Slice(
        slice_name='Gender Wise Admission',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(new_wh_lt_3sd+new_muac_lt_115+new_both+new_edema+new_relapse)',
                    'label': 'Admissions',
                    'hasCustomLabel': True
                }
            ],
            'groupby': ['gender'],
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

    # Bar Chart: SC Discharge Performance Indicator (Stacked)
    charts.append(Slice(
        slice_name='Discharge Performance Indicator',
        datasource_type='table',
        datasource_id=dataset.id,
        viz_type='echarts_timeseries_bar',
        params=json.dumps({
            'datasource': f'{dataset.id}__table',
            'viz_type': 'echarts_timeseries_bar',
            'x_axis': {
                'expressionType': 'SQL',
                'label': 'Month',
                'sqlExpression': 'CONCAT(year, \'-\', LPAD(month, 2, \'0\'))'
            },
            'metrics': [
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(recovered) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Recovered',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(transfer_to_otp) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Transfer to OTP',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(death) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Death',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(defaulted) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Defaulted',
                    'hasCustomLabel': True
                },
                {
                    'expressionType': 'SQL',
                    'sqlExpression': 'SUM(non_responder) * 100.0 / NULLIF(SUM(recovered + death + non_responder + defaulted + exit_others + transfer_to_otp + medical_transfer), 0)',
                    'label': 'Non Responder',
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
            'legendOrientation': 'bottom',
            'rich_tooltip': True,
            'y_axis_format': ',.1f',
            'stack': 'Stack',
            'truncateXAxis': True,
            'y_axis_bounds': [0, 100]
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

    # Configure native filters with cascading and NULL exclusion
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
            'cascadeParentIds': ['NATIVE_FILTER-year'],
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
            'name': 'SC',
            'filterType': 'filter_select',
            'targets': [{
                'column': {'name': 'camp_site'},
                'datasetId': dataset.id,
                'datasetUuid': str(dataset.uuid)
            }],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}, 'ownState': {}},
            'cascadeParentIds': ['NATIVE_FILTER-implementing-partner'],
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
        }
    ]

    # Update dashboard metadata with native filters and cross-filtering
    dashboard.json_metadata = json.dumps({
        'color_scheme': '',
        'refresh_frequency': 0,
        'expanded_slices': {},
        'label_colors': {},
        'shared_label_colors': ['Transfer to OTP', 'Recovered', 'Medical Transfer', 'Defaulted', 'Unknown', 'Non Responder', 'Death', 'Male', 'Female'],
        'map_label_colors': {
            'Transfer to OTP': '#004960',
            'Recovered': '#FCC550',
            'Medical Transfer': '#408184',
            'Defaulter': '#408184',
            'Unknown': '#EE5960',
            'Non-responder': '#2893B3',
            'Death': '#FF874E',
            'Defaulted': '#2893B3',
            'Non Responder': '#484E5A',
            'Male': '#1FA8C9',
            'Female': '#454E7C',
            'OTP Transfer': '#6BD3B3'
        },
        'timed_refresh_immune_slices': [],
        'cross_filters_enabled': True,
        'default_filters': '{}',
        'native_filter_configuration': native_filters
    })

    db.session.commit()

    print(f"✓ Created {len(charts)} charts:")
    for i, chart in enumerate(charts, 1):
        print(f"  {i}. {chart.slice_name} ({chart.viz_type})")

    print(f"✓ Configured {len(native_filters)} native filters with cascading:")
    print(f"  - Year (parent)")
    print(f"  - Month")
    print(f"  - Implementing Partner (cascades from Year)")
    print(f"  - SC/Camp Site (cascades from Implementing Partner)")
    print(f"  - Gender, Age Group, Program Partner")

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print(f"\nDashboard URL: http://localhost:8088/superset/dashboard/{DASHBOARD_SLUG}/")
    print(f"Dataset ID: {dataset.id}")
    print(f"Dashboard ID: {dashboard.id}")
    print(f"Dataset UUID: {dataset.uuid}")
    print()
