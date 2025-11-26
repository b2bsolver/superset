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

    # Step 2: Create/Update Dataset
    print(f"\n[2/4] Setting up Dataset...")
    dataset = db.session.query(SqlaTable).filter_by(
        database_id=database.id,
        table_name=TABLE_NAME
    ).first()

    # SQL query to join with infs table for latitude/longitude
    # Note: otp_reports already has program_partner, implementing_partner, camp_site
    dataset_sql = """
        SELECT
            otp.*,
            infs.latitude,
            infs.longitude,
            infs.title as inf_title
        FROM otp_reports as otp
        LEFT JOIN infs ON otp.inf_id = infs.id
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

    # Save all charts
    for chart in charts:
        db.session.add(chart)
    db.session.commit()

    # Add charts to dashboard
    dashboard.slices.extend(charts)

    # Get all chart IDs
    chart_ids = [chart.id for chart in charts]

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

    print(f"✓ Configured {len(native_filters)} native filters:")
    print(f"  - Year, Month, Gender, Age Group, Program Partner, Implementing Partner")

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print(f"\nDashboard URL: http://localhost:8088/superset/dashboard/{DASHBOARD_SLUG}/")
    print(f"Dataset ID: {dataset.id}")
    print(f"Dashboard ID: {dashboard.id}")
    print(f"Dataset UUID: {dataset.uuid}")
    print()
