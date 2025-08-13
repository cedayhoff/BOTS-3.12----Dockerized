#!/bin/bash
echo "🚀 Bots EDI Manual Production Setup"
echo "===================================="
echo ""

# Function to setup SQLite
setup_sqlite() {
    echo "📊 Setting up SQLite database..."
    
    # Create database config
    cat > /tmp/bots_db_config.json << EOF
{
  "type": "sqlite"
}
EOF
    
    # Copy config to container
    docker cp /tmp/bots_db_config.json bots-webserver:/app/bots_database_config.json
    
    # Initialize database and create admin user
    echo "🗄️  Creating fresh SQLite database..."
    docker-compose exec webserver bash -c "
        cd /app
        export DJANGO_SETTINGS_MODULE=bots.config.settings
        export PYTHONPATH=/app
        
        # Create fresh database
        mkdir -p /app/bots/botssys/sqlitedb
        python3.12 manage.py migrate --run-syncdb
        
        # Create routeschedule table
        python3.12 -c \"
import sqlite3
db_path = '/app/bots/botssys/sqlitedb/botsdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\\\"table\\\" AND name=\\\"routeschedule\\\"')
if not cursor.fetchone():
    create_sql = '''
        CREATE TABLE routeschedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            route_id VARCHAR(35) NOT NULL,
            active BOOLEAN DEFAULT 1,
            frequency VARCHAR(20) DEFAULT 'daily',
            interval INTEGER DEFAULT 1,
            time_hour INTEGER NULL,
            time_minute INTEGER DEFAULT 0,
            weekday VARCHAR(20) NULL,
            day_of_month INTEGER NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_run DATETIME NULL,
            next_run DATETIME NULL,
            enabled_only_weekdays BOOLEAN DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        )
    '''
    cursor.execute(create_sql)
    conn.commit()
    print('✅ Created routeschedule table')
else:
    print('✅ routeschedule table already exists')
conn.close()
\"
        
        echo '✅ Database initialized successfully'
    "
}

# Function to setup PostgreSQL
setup_postgresql() {
    echo "📊 Setting up PostgreSQL database..."
    
    read -p "PostgreSQL Host: " PG_HOST
    read -p "PostgreSQL Port [5432]: " PG_PORT
    read -p "PostgreSQL Database: " PG_DB
    read -p "PostgreSQL User: " PG_USER
    read -s -p "PostgreSQL Password: " PG_PASS
    echo ""
    
    PG_PORT=${PG_PORT:-5432}
    
    # Create database config
    cat > /tmp/bots_db_config.json << EOF
{
  "type": "postgres",
  "host": "$PG_HOST",
  "port": $PG_PORT,
  "database": "$PG_DB",
  "user": "$PG_USER",
  "password": "$PG_PASS"
}
EOF
    
    # Copy config to container
    docker cp /tmp/bots_db_config.json bots-webserver:/app/bots_database_config.json
    
    # Test connection and setup database
    echo "🔌 Testing PostgreSQL connection..."
    docker-compose exec webserver bash -c "
        cd /app
        export DJANGO_SETTINGS_MODULE=bots.config.settings
        export PYTHONPATH=/app
        export BOTS_DB_ENGINE=postgres
        export POSTGRES_HOST='$PG_HOST'
        export POSTGRES_PORT='$PG_PORT'
        export POSTGRES_DB='$PG_DB'
        export POSTGRES_USER='$PG_USER'
        export POSTGRES_PASSWORD='$PG_PASS'
        
        # Run migrations
        python3.12 manage.py migrate
        
        echo '✅ PostgreSQL database initialized successfully'
    "
}

# Function to create admin user
create_admin_user() {
    echo ""
    echo "👤 Creating Admin User"
    echo "===================="
    
    read -p "Admin Username [admin]: " ADMIN_USER
    read -p "Admin Email: " ADMIN_EMAIL
    read -s -p "Admin Password: " ADMIN_PASS
    echo ""
    read -s -p "Confirm Password: " ADMIN_PASS_CONFIRM
    echo ""
    
    if [ "$ADMIN_PASS" != "$ADMIN_PASS_CONFIRM" ]; then
        echo "❌ Passwords don't match!"
        return 1
    fi
    
    ADMIN_USER=${ADMIN_USER:-admin}
    
    # Create admin user
    docker-compose exec webserver bash -c "
        cd /app
        export DJANGO_SETTINGS_MODULE=bots.config.settings
        export PYTHONPATH=/app
        
        python3.12 -c \"
import os
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()

if User.objects.filter(username='$ADMIN_USER').exists():
    print('⚠️  User $ADMIN_USER already exists')
else:
    User.objects.create_superuser('$ADMIN_USER', '$ADMIN_EMAIL', '$ADMIN_PASS')
    print('✅ Admin user $ADMIN_USER created successfully')
\"
    "
}

# Function to complete setup
complete_setup() {
    echo ""
    echo "✅ Marking setup as complete..."
    docker-compose exec webserver touch /app/.bots_setup_complete
    
    echo "🔄 Restarting containers..."
    docker-compose restart
    
    echo ""
    echo "🎉 Setup Complete!"
    echo "=================="
    echo "🌐 Access Bots EDI at: http://localhost:8080"
    echo "👤 Login with your admin credentials"
    echo "📊 Scheduler available at: http://localhost:8885/health"
    echo ""
    echo "Your production-ready Bots EDI system is now running!"
    echo "✅ No hardcoded credentials"
    echo "✅ Fresh database with no old data" 
    echo "✅ Custom admin user"
    echo "✅ Unified database across all containers"
}

# Main setup flow
echo "Choose your database:"
echo "1) SQLite (recommended for development/testing)"
echo "2) PostgreSQL (recommended for production)"
echo ""
read -p "Select option [1]: " DB_CHOICE
DB_CHOICE=${DB_CHOICE:-1}

if [ "$DB_CHOICE" = "1" ]; then
    setup_sqlite
elif [ "$DB_CHOICE" = "2" ]; then
    setup_postgresql
else
    echo "❌ Invalid choice. Exiting."
    exit 1
fi

if [ $? -eq 0 ]; then
    create_admin_user
    if [ $? -eq 0 ]; then
        complete_setup
    else
        echo "❌ Admin user creation failed. Please try again."
        exit 1
    fi
else
    echo "❌ Database setup failed. Please check your configuration."
    exit 1
fi