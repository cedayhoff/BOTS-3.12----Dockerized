#!/usr/bin/env python3
"""
Simple script to create the routeschedule table in the Bots database
"""

import os
import sys
import sqlite3

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_schedule_table():
    """Create the routeschedule table in the Bots database"""
    
    # Find the database file
    db_path = None
    possible_paths = [
        'botsdb',
        'config/botsdb', 
        '/app/botsdb',
        '/app/config/botsdb',
        '/app/bots/usersys/botsdb',
        '/app/bots/install/botsdb',
        '/app/bots/botssys/sqlitedb/botsdb',
        'bots/usersys/botsdb',
        'bots/install/botsdb'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("Error: Could not find Bots database file")
        return False
    
    print(f"Using database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='routeschedule'")
        if cursor.fetchone():
            print("Table 'routeschedule' already exists")
            return True
        
        # Create the table
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
        
        print("Successfully created 'routeschedule' table")
        
        # Create a sample schedule for testing
        sample_sql = '''
            INSERT INTO routeschedule 
            (name, route_id, active, frequency, time_hour, time_minute)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        cursor.execute(sample_sql, (
            'Daily Test Schedule',
            'test_route',
            1,  # active
            'daily',
            9,   # 9 AM
            0    # 0 minutes
        ))
        
        conn.commit()
        print("Added sample schedule for testing")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating table: {str(e)}")
        return False

if __name__ == '__main__':
    print("Creating routeschedule table in Bots database...")
    success = create_schedule_table()
    sys.exit(0 if success else 1)