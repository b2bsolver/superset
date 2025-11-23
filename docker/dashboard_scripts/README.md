# Dashboard Setup Scripts

This folder contains individual scripts to create complete dashboards (datasets + charts) for each report type.

## 📁 Structure

```
dashboard_scripts/
├── README.md                           # This file
├── setup_all_dashboards.py            # Master script to run all dashboards
├── setup_iycf_dashboard.py            # IYCF Monthly Reports
├── setup_new_arrival_dashboard.py     # New Arrival Reports
├── setup_under_six_dashboard.py       # Under Six Monthly Reports
├── cleanup_examples.py                # Remove example data (partial)
└── cleanup_all_examples.py            # Remove ALL example data (complete)
```

## 🚀 Quick Start

### Option 1: Setup All Dashboards at Once

```bash
docker exec superset_app python /app/docker/dashboard_scripts/setup_all_dashboards.py
```

This will create all three dashboards in sequence.

### Option 2: Setup Individual Dashboards

Run each script individually:

```bash
# IYCF Monthly Reports Dashboard
docker exec superset_app python /app/docker/dashboard_scripts/setup_iycf_dashboard.py

# New Arrival Reports Dashboard
docker exec superset_app python /app/docker/dashboard_scripts/setup_new_arrival_dashboard.py

# Under Six Monthly Reports Dashboard
docker exec superset_app python /app/docker/dashboard_scripts/setup_under_six_dashboard.py
```

## 📊 What Each Script Does

Each script performs the following steps automatically:

1. **Find Database** - Locates the MySQL database connection
2. **Create/Update Dataset** - Creates table dataset or refreshes if exists
3. **Create/Update Dashboard** - Creates dashboard or clears existing charts
4. **Create Charts** - Generates all visualization charts with proper configuration

## 📈 Dashboard Details

### 1. IYCF Monthly Reports Dashboard

**Charts Created (8):**
- 5 Big Number cards:
  - Total Staff Trained
  - Total Counselors Trained
  - Total Volunteers Trained
  - Total IYCF Services
  - Issues Resolved (6-23m)
- Monthly Training Progress (Line Chart)
- Counseling Sessions (Bar Chart)
- Education Sessions Trend (Area Chart)

**URL:** `/superset/dashboard/iycf-monthly-dashboard/`

### 2. New Arrival Reports Dashboard

**Charts Created (5):**
- 1 Big Number card:
  - Total Arrivals
- Arrivals Over Time (Line Chart)
- Arrivals by Protection Point (Bar Chart)
- Arrivals by Implementing Partner (Pie Chart)
- Arrivals Distribution (Sunburst)

**URL:** `/superset/dashboard/new-arrival-dashboard/`

### 3. Under Six Monthly Reports Dashboard

**Charts Created (8):**
- 4 Big Number cards:
  - Total RAPID Cases
  - Inpatient Referrals
  - Total Referrals
  - Reduced Visit Frequency
- Monthly Capacity Training (Line Chart)
- Referral Services Breakdown (Bar Chart)
- Services After 6 Months (Bar Chart)
- Higher PSS Referrals Trend (Area Chart)

**URL:** `/superset/dashboard/under-six-monthly-dashboard/`

## 🔧 Configuration

All scripts use the following default configuration:

- **Database Name:** `MySQL`
- **Schema:** Empty (default schema)
- **Date Filters:** Temporal range on `created_at` or `from_date`
- **Color Scheme:** `supersetColors`
- **Chart Style:** Following OTP dashboard patterns

To change the database name, edit the `DATABASE_NAME` constant in each script.

## 🔄 Re-running Scripts

You can safely re-run any script multiple times:

- If the dataset exists: Metadata will be refreshed
- If the dashboard exists: Old charts will be deleted and recreated
- Charts are always recreated from scratch

This is useful for:
- Updating chart configurations
- Adding new charts
- Fixing issues

## 🎨 Chart Customization

To customize charts, edit the respective script and modify the chart parameters in the `charts.append(Slice(...))` sections.

Key parameters you can customize:
- `metrics`: SQL expressions for data aggregation
- `groupby`: Columns to group by
- `color_scheme`: Color palette
- `y_axis_format`: Number formatting (e.g., `,.0f`, `,.2f`, `$,.0f`)
- `show_legend`: Enable/disable legend
- `opacity`: Chart transparency (for area charts)

## 📝 Notes

- All charts use SQL expressions for metrics (following OTP dashboard pattern)
- Time-based grouping uses `CONCAT(year, '-', LPAD(month, 2, '0'))` for month-year format
- Filters use TEMPORAL_RANGE operator for date filtering
- Big number cards use `big_number_total` visualization type

## 🐛 Troubleshooting

### Database not found
```
✗ Database 'MySQL' not found!
```
**Solution:** Check database name in Superset. Update `DATABASE_NAME` in the script if different.

### Table doesn't exist
The script will fail if the table doesn't exist in the database. Ensure tables exist:
- `iycf_monthly_reports`
- `new_arrival_reports`
- `under_six_monthly_reports`

### Permission errors
Ensure the database user has SELECT permissions on the tables.

## 🔗 SSO Integration

Dashboard URLs are configured in `docker/pythonpath_dev/superset_config.py`:

```python
DASHBOARD_URLS = {
    'otp': '/superset/dashboard/otp-dashboard/',
    'sc': '/superset/dashboard/13/',
    'iycf': '/superset/dashboard/iycf-monthly-dashboard/',
    'new_arrival': '/superset/dashboard/new-arrival-dashboard/',
    'under_six': '/superset/dashboard/under-six-monthly-dashboard/',
}
```

Users can be redirected to specific dashboards via SSO using these keys.

## 🧹 Cleanup Scripts

### Remove ALL Example/Test Data

To keep ONLY your custom MySQL report dashboards and remove all Superset examples:

```bash
docker exec superset_app python /app/docker/dashboard_scripts/cleanup_all_examples.py
```

This will remove:
- All example dashboards (World Bank, Misc Charts, etc.)
- All example datasets (birth_names, flights, etc.)
- All example database connections (keeping only MySQL)
- All orphaned charts

**Keeps only:**
- Your 4 custom dashboards: OTP, IYCF, New Arrival, Under Six
- Your 4 custom datasets from MySQL
- MySQL database connection

⚠️ **Warning:** This action cannot be undone! The script will ask for confirmation before proceeding.

### What Gets Removed

The cleanup script removes:
- ❌ Example dashboards (World Bank's Data, Video Game Sales, etc.)
- ❌ Example datasets (birth_names, flights, wb_health_population, etc.)
- ❌ Example database connections (examples database)
- ❌ All orphaned charts not attached to your dashboards

### What Gets Kept

The cleanup script keeps:
- ✅ OTP Dashboard
- ✅ IYCF Monthly Dashboard
- ✅ New Arrival Dashboard
- ✅ Under Six Monthly Dashboard
- ✅ All charts in above dashboards
- ✅ All 4 custom datasets (otp_reports, iycf_monthly_reports, new_arrival_reports, under_six_monthly_reports)
- ✅ MySQL database connection
