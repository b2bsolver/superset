#!/usr/bin/env python3
"""
Superset Initial Setup Script
Comprehensive setup for Superset: cleanup, database connection, and user roles
Run: docker compose exec superset python /app/docker/dashboard_scripts/setup_superset.py
"""
import getpass
import os
import shutil
import sys
sys.path.insert(0, '/app')
from superset.app import create_app

app = create_app()


def cleanup_all_data():
    """Remove all existing data and reset auto-increment IDs"""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.core import Database

    print("\n" + "=" * 80)
    print("CLEANUP: REMOVE ALL EXISTING DATA")
    print("=" * 80)
    print("\n⚠️  WARNING: This will remove:")
    print("  - ALL dashboards")
    print("  - ALL charts")
    print("  - ALL datasets")
    print("  - ALL database connections")

    response = input("\nDo you want to cleanup existing data? (yes/no) [no]: ").strip().lower()
    if response != 'yes':
        print("Skipping cleanup...")
        return

    # Count before deletion
    total_dashboards = db.session.query(Dashboard).count()
    total_charts = db.session.query(Slice).count()
    total_datasets = db.session.query(SqlaTable).count()
    total_databases = db.session.query(Database).count()

    print(f"\n📊 Current State:")
    print(f"  - Dashboards: {total_dashboards}")
    print(f"  - Charts: {total_charts}")
    print(f"  - Datasets: {total_datasets}")
    print(f"  - Database Connections: {total_databases}")

    print("\n[1/5] Removing ALL Dashboards...")
    all_dashboards = db.session.query(Dashboard).all()
    for dashboard in all_dashboards:
        for slice in list(dashboard.slices):
            dashboard.slices.remove(slice)
        db.session.delete(dashboard)
    db.session.commit()
    print(f"✓ Removed {len(all_dashboards)} dashboards")

    print("\n[2/5] Removing ALL Charts...")
    all_charts = db.session.query(Slice).all()
    for chart in all_charts:
        db.session.delete(chart)
    db.session.commit()
    print(f"✓ Removed {len(all_charts)} charts")

    print("\n[3/5] Removing ALL Datasets...")
    all_datasets = db.session.query(SqlaTable).all()
    for dataset in all_datasets:
        db.session.delete(dataset)
    db.session.commit()
    print(f"✓ Removed {len(all_datasets)} datasets")

    print("\n[4/5] Removing ALL Database Connections...")
    all_databases = db.session.query(Database).all()
    for database in all_databases:
        db.session.delete(database)
    db.session.commit()
    print(f"✓ Removed {len(all_databases)} database connections")

    print("\n[5/5] Resetting Auto-Increment IDs...")
    engine = db.session.get_bind()
    dialect_name = engine.dialect.name

    tables_to_reset = [
        ('dashboards', Dashboard.__tablename__),
        ('slices', Slice.__tablename__),
        ('tables', SqlaTable.__tablename__),
        ('dbs', Database.__tablename__)
    ]

    reset_count = 0
    for display_name, table_name in tables_to_reset:
        try:
            if dialect_name == 'mysql':
                db.session.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1")
                reset_count += 1
            elif dialect_name == 'postgresql':
                db.session.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1")
                reset_count += 1
            elif dialect_name == 'sqlite':
                db.session.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                reset_count += 1
        except Exception:
            pass

    db.session.commit()
    print(f"✓ Reset auto-increment IDs for {reset_count} tables ({dialect_name})")
    print("✓ Cleanup complete!\n")


def setup_database():
    """Setup MySQL database connection"""
    from superset import db
    from superset.models.core import Database

    print("=" * 80)
    print("DATABASE CONNECTION SETUP")
    print("=" * 80)

    print("\n--- MySQL Database Configuration ---")
    db_name = input("Display name for database in Superset [Enim]: ").strip() or "Enim"
    host = input("MySQL host [db]: ").strip() or "db"
    port = input("MySQL port [3306]: ").strip() or "3306"

    try:
        port = int(port)
    except ValueError:
        print("Invalid port, using default 3306")
        port = 3306

    user = input("MySQL username [root]: ").strip() or "root"
    password = getpass.getpass("MySQL password: ")
    while not password:
        print("MySQL password is required!")
        password = getpass.getpass("MySQL password: ")

    database = input("MySQL database name [enim_db]: ").strip() or "enim_db"

    print(f"\nConfiguration:")
    print(f"  Display Name: {db_name}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  User: {user}")

    # Build SQLAlchemy URI
    sqlalchemy_uri = f"mysql://{user}:{password}@{host}:{port}/{database}"

    # Check if database already exists
    existing_db = db.session.query(Database).filter_by(database_name=db_name).first()

    if existing_db:
        print(f"\n  ℹ Database '{db_name}' already exists (ID: {existing_db.id})")
        print(f"  Updating configuration...")
        existing_db.sqlalchemy_uri = sqlalchemy_uri
        existing_db.expose_in_sqllab = True
        existing_db.allow_ctas = True
        existing_db.allow_cvas = True
        existing_db.allow_dml = True
        db.session.commit()
        print(f"  ✓ Database configuration updated")
        database_id = existing_db.id
    else:
        print(f"\n  Creating new database '{db_name}'...")
        new_db = Database(
            database_name=db_name,
            sqlalchemy_uri=sqlalchemy_uri,
            expose_in_sqllab=True,
            allow_ctas=True,
            allow_cvas=True,
            allow_dml=True,
        )
        db.session.add(new_db)
        db.session.commit()
        print(f"  ✓ Database created successfully (ID: {new_db.id})")
        database_id = new_db.id

    # Test connection
    print(f"\n  Testing database connection...")
    try:
        database_obj = db.session.query(Database).filter_by(id=database_id).first()
        engine = database_obj.get_sqla_engine()
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            result.fetchone()
        print(f"  ✓ Database connection test successful")
    except Exception as e:
        print(f"  ✗ Database connection test failed: {e}")
        print(f"  Note: Database was created but connection test failed.")

    print(f"\n✓ Database setup complete!")
    return database_id


def setup_enim_users_role(database_id: int) -> None:
    """Setup read-only role for external users"""
    from superset import db, security_manager
    from superset.models.core import Database

    ROLE_NAME = 'Enim Users'

    print("\n" + "=" * 80)
    print("USER ROLE SETUP")
    print("=" * 80)

    # Check if role already exists
    role = security_manager.find_role(ROLE_NAME)

    if role:
        print(f"\n  ℹ Role '{ROLE_NAME}' already exists")
        print(f"  Updating permissions...")
        role.permissions = []
        db.session.commit()
    else:
        print(f"\n  Creating role '{ROLE_NAME}'...")
        role = security_manager.add_role(ROLE_NAME)
        db.session.commit()
        print(f"  ✓ Role created")

    print(f"\n  Configuring permissions for read-only dashboard access...")

    permissions_to_add = [
        # Dashboard permissions
        ('can_read', 'Dashboard'),
        ('can_list', 'Dashboard'),
        ('can_dashboard', 'Superset'),
        ('can_explore', 'Superset'),
        ('can_explore_json', 'Superset'),

        # Chart permissions
        ('can_read', 'Chart'),
        ('can_list', 'Chart'),
        ('can_get', 'Chart'),
        ('can_data', 'Chart'),
        ('can_get_data', 'Chart'),

        # Dataset permissions
        ('can_read', 'Dataset'),
        ('can_list', 'Dataset'),
        ('can_get', 'Dataset'),
        ('can_get_or_create_dataset', 'Dataset'),

        # Database permissions (read-only)
        ('can_read', 'Database'),
        ('can_list', 'Database'),

        # Query permissions
        ('can_read', 'Query'),

        # API permissions
        ('can_read', 'DashboardRestApi'),
        ('can_get', 'DashboardRestApi'),
        ('can_read', 'ChartRestApi'),
        ('can_get', 'ChartRestApi'),
        ('can_data', 'ChartRestApi'),
        ('can_read', 'DatasetRestApi'),
        ('can_get', 'DatasetRestApi'),

        # Essential Superset permissions
        ('can_userinfo', 'UserDBModelView'),
        ('can_csrf_token', 'Superset'),
        ('can_recent_activity', 'Log'),
        ('can_recent_activity', 'Superset'),
        ('can_fave_dashboards', 'Superset'),
        ('can_favstar', 'Superset'),
        ('can_slice', 'Superset'),
        ('can_log', 'Superset'),
        ('can_dashboard_permalink', 'Superset'),
        ('can_explore_permalink', 'Superset'),
        ('can_warm_up_cache', 'Superset'),

        # Filter permissions
        ('can_read', 'SavedQuery'),

        # Menu access
        ('menu_access', 'Dashboards'),
        ('menu_access', 'Charts'),

        # Security permissions
        ('can_read', 'SecurityApi'),
        ('can_csrf_token', 'SecurityApi'),

        # Annotation permissions
        ('can_read', 'Annotation'),
        ('can_read', 'AnnotationLayer'),

        # Row level security
        ('can_read', 'RowLevelSecurityFilter'),

        # Embedded dashboard permissions
        ('can_dashboard_embedded', 'Superset'),
    ]

    permission_count = 0
    for perm_name, view_name in permissions_to_add:
        perm_view = security_manager.find_permission_view_menu(perm_name, view_name)

        if not perm_view:
            permission = security_manager.find_permission(perm_name)
            view_menu = security_manager.find_view_menu(view_name)

            if permission and view_menu:
                security_manager.add_permission_view_menu(perm_name, view_name)
                perm_view = security_manager.find_permission_view_menu(perm_name, view_name)

        if perm_view and perm_view not in role.permissions:
            role.permissions.append(perm_view)
            permission_count += 1

    db.session.commit()
    print(f"  ✓ Added {permission_count} permissions to role")
    database = db.session.get(Database, database_id)
    if database:
        print(f"\n  Granting database access for '{database.database_name}'...")
        db_perm = security_manager.find_permission_view_menu(
            "database_access", database.perm
        )
        if not db_perm:
            security_manager.add_permission_view_menu("database_access", database.perm)
            db_perm = security_manager.find_permission_view_menu(
                "database_access", database.perm
            )
        if db_perm and db_perm not in role.permissions:
            role.permissions.append(db_perm)
            db.session.commit()
            print("  ✓ Database access permission added to role")
        else:
            print("  ℹ Role already has database access permission")

    print(f"\n✓ Role setup complete!")
    print(f"  Total Permissions: {len(role.permissions)}")


def setup_custom_logo():
    """Copy custom logo to static assets directory"""
    print("\n" + "=" * 80)
    print("CUSTOM LOGO SETUP")
    print("=" * 80)

    # Source logo path (from dashboard_scripts)
    source_logo = "/app/docker/dashboard_scripts/unicef.png"
    # Target logo path (static assets)
    target_logo = "/app/superset/static/assets/images/unicef.png"

    if not os.path.exists(source_logo):
        print(f"\n  ⚠️  Warning: Logo file not found at {source_logo}")
        print("  Skipping logo setup...")
        return False

    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(target_logo), exist_ok=True)

        # Copy logo file
        shutil.copy2(source_logo, target_logo)
        print(f"\n  ✓ Logo copied to {target_logo}")

        # Set proper permissions
        os.chmod(target_logo, 0o644)
        print(f"  ✓ Logo permissions set")

        return True
    except Exception as e:
        print(f"\n  ✗ Failed to copy logo: {e}")
        return False


def main():
    """Main setup orchestration"""
    print("=" * 80)
    print("SUPERSET INITIAL SETUP")
    print("=" * 80)
    print("\nThis script will help you set up Superset:")
    print("  1. (Optional) Cleanup existing data")
    print("  2. Configure MySQL database connection")
    print("  3. Setup 'Enim Users' role for read-only access")
    print("  4. Setup custom logo")

    with app.app_context():
        # Step 1: Optional cleanup
        cleanup_all_data()

        # Step 2: Setup database
        database_id = setup_database()

        # Step 3: Setup user role
        setup_enim_users_role(database_id)

        # Step 4: Setup custom logo
        logo_success = setup_custom_logo()

        # Final summary
        print("\n" + "=" * 80)
        print("SETUP COMPLETE!")
        print("=" * 80)
        print(f"\n✓ Database configured (ID: {database_id})")
        print(f"✓ 'Enim Users' role configured")
        if logo_success:
            print(f"✓ Custom logo configured")
        print()


if __name__ == "__main__":
    main()
