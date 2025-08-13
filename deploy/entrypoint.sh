#!/bin/bash
set -e

echo "🚀 Starting Bots EDI System..."

# Check if first-time setup is needed
if [ ! -f /app/.bots_setup_complete ]; then
    echo "⚠️  First-time setup required!"
    echo "📋 Please run the setup interface first:"
    echo "    docker run -p 9000:9000 -v bots-data:/app your-bots-image python3.12 bots_setup.py"
    echo "    Or visit the setup page if already running"
    
    # If this is a webserver, run the setup interface and redirect servers
    if [[ "$*" == *"bots-webserver.py"* ]]; then
        echo "🌐 Starting setup interface on port 9000..."
        python3.12 bots_setup.py &
        SETUP_PID=$!
        
        # Start redirect servers on main Bots ports
        echo "🔄 Starting redirect servers on main ports..."
        python3.12 setup_redirect.py 8080 &  # Main web interface
        REDIRECT_8080_PID=$!
        python3.12 setup_redirect.py 8881 &  # Alternative web port
        REDIRECT_8881_PID=$!
        
        # Wait for setup to complete or timeout after 10 minutes
        for i in {1..600}; do
            if [ -f /app/.bots_setup_complete ]; then
                echo "✅ Setup completed! Killing setup and redirect servers..."
                kill $SETUP_PID 2>/dev/null || true
                kill $REDIRECT_8080_PID 2>/dev/null || true
                kill $REDIRECT_8881_PID 2>/dev/null || true
                break
            fi
            sleep 1
        done
        
        if [ ! -f /app/.bots_setup_complete ]; then
            echo "❌ Setup timeout! Please complete setup manually."
            exit 1
        fi
    else
        # For non-webserver containers, start redirect servers on their ports
        echo "🔄 Starting redirect server for this service..."
        
        # Determine which port to redirect based on the service
        if [[ "$*" == *"bots-jobqueueserver.py"* ]]; then
            python3.12 setup_redirect.py 28082 &  # Job queue port
            REDIRECT_PID=$!
        elif [[ "$*" == *"bots-dirmonitor.py"* ]]; then
            python3.12 setup_redirect.py 8888 &   # Directory monitor port
            REDIRECT_PID=$!
        elif [[ "$*" == *"bots-scheduler.py"* ]]; then
            python3.12 setup_redirect.py 8884 &   # Scheduler port
            REDIRECT_PID=$!
        fi
        
        # Wait for setup to be completed by webserver container
        echo "⏳ Waiting for setup to be completed by webserver container..."
        while [ ! -f /app/.bots_setup_complete ]; do
            sleep 5
        done
        
        # Kill redirect server once setup is complete
        if [ ! -z "$REDIRECT_PID" ]; then
            kill $REDIRECT_PID 2>/dev/null || true
        fi
        
        echo "✅ Setup detected as complete, continuing..."
    fi
fi

# Load database configuration if it exists
if [ -f /app/bots_database_config.json ]; then
    echo "📊 Loading database configuration..."
    
    # Extract database type and set environment variables
    DB_TYPE=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['type'])")
    
    if [ "$DB_TYPE" = "postgres" ]; then
        export BOTS_DB_ENGINE="postgres"
        export POSTGRES_HOST=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['host'])")
        export POSTGRES_PORT=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['port'])")
        export POSTGRES_DB=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['database'])")
        export POSTGRES_USER=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['user'])")
        export POSTGRES_PASSWORD=$(python3.12 -c "import json; config=json.load(open('/app/bots_database_config.json')); print(config['password'])")
        echo "✅ PostgreSQL configuration loaded"
    else
        export BOTS_DB_ENGINE="sqlite"
        echo "✅ SQLite configuration loaded"
    fi
fi

# Database initialization based on configured type
if [ "$BOTS_DB_ENGINE" != "postgres" ]; then
    echo "🗄️  Initializing SQLite database..."
    
    # Ensure SQLite directory exists
    mkdir -p /app/bots/botssys/sqlitedb
    
    # Create fresh database using Django migrations if none exists
    if [ ! -f /app/bots/botssys/sqlitedb/botsdb ]; then
        echo "📋 Creating fresh SQLite database with Django migrations..."
        
        # Set Django environment
        export DJANGO_SETTINGS_MODULE=bots.config.settings
        export PYTHONPATH=/app
        
        # Run Django migrations to create fresh database
        cd /app
        python3.12 manage.py migrate --run-syncdb
        
        echo "✅ Fresh SQLite database created"
    else
        echo "✅ Using existing SQLite database"
    fi
    
    # Ensure routeschedule table exists
    python3.12 -c "
import sqlite3, os
db_path = '/app/bots/botssys/sqlitedb/botsdb'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='routeschedule'\")
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
"
  
    # Keep local copies for non-database files
    if [ ! -f /app/bots/usersys/bots.ini ]; then
        cp /app/bots/install/bots.ini /app/bots/usersys/bots.ini
    fi
else
    echo "🗄️  Initializing PostgreSQL database..."
    echo "📊 Running Django migrations..."
    python3.12 manage.py makemigrations bots
    python3.12 manage.py migrate
    python3.12 manage.py collectstatic --noinput
    echo "✅ PostgreSQL initialization complete"
fi

echo "🎯 Starting application: $@"
exec "$@"