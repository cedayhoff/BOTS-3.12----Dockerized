#!/usr/bin/env python
"""
Bots EDI Scheduler Service

This service provides scheduled execution of Bots routes based on user-defined schedules.
It allows users to:
- Schedule routes to run at specific times
- Set up recurring schedules (daily, weekly, monthly)
- Monitor scheduled job status
- Manually trigger route runs
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
import subprocess
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import schedule

# Import bots modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bots import botsinit
from bots import botsglobal

start_time = time.time()

class SchedulerHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            uptime = time.time() - start_time
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get scheduler status
            status = {
                "status": "healthy",
                "uptime": f"{uptime:.2f}s",
                "scheduled_jobs": len(schedule.jobs),
                "next_run": str(schedule.next_run()) if schedule.jobs else None,
                "service": "bots-scheduler"
            }
            self.wfile.write(json.dumps(status).encode())
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Detailed status
            jobs_info = []
            for job in schedule.jobs:
                jobs_info.append({
                    "job": str(job.job_func),
                    "next_run": str(job.next_run),
                    "interval": job.interval,
                    "unit": job.unit
                })
            
            status = {
                "service": "bots-scheduler",
                "total_jobs": len(schedule.jobs),
                "jobs": jobs_info,
                "last_check": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(status, indent=2).encode())
        elif self.path == '/reload':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Trigger reload of custom schedules
            try:
                if hasattr(self.server, 'scheduler_instance'):
                    self.server.scheduler_instance.load_custom_schedules()
                    result = {"status": "success", "message": "Schedules reloaded"}
                else:
                    result = {"status": "error", "message": "Scheduler instance not available"}
            except Exception as e:
                result = {"status": "error", "message": str(e)}
            
            self.wfile.write(json.dumps(result).encode())
        
        elif self.path == '/schedules':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get all schedules from database
            try:
                if hasattr(self.server, 'scheduler_instance'):
                    schedules = self.server.scheduler_instance.get_all_schedules()
                    result = {"status": "success", "schedules": schedules}
                else:
                    result = {"status": "error", "message": "Scheduler instance not available"}
            except Exception as e:
                result = {"status": "error", "message": str(e)}
            
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/schedules':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                if hasattr(self.server, 'scheduler_instance'):
                    result = self.server.scheduler_instance.create_schedule(data)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_error(500)
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                result = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(result).encode())
        else:
            self.send_error(404)
    
    def do_DELETE(self):
        if self.path.startswith('/schedules/'):
            schedule_id = self.path.split('/')[-1]
            
            try:
                if hasattr(self.server, 'scheduler_instance'):
                    result = self.server.scheduler_instance.delete_schedule(int(schedule_id))
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_error(500)
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                result = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(result).encode())
        else:
            self.send_error(404)

class BotsScheduler:
    def __init__(self):
        if botsglobal.logger is None:
            import logging
            self.logger = logging.getLogger('bots.scheduler')
        else:
            self.logger = botsglobal.logger
        self.running = True
        
    def run_route(self, route_name):
        """Execute a specific route using bots-engine"""
        try:
            self.logger.info(f'Scheduler: Running route "{route_name}"')
            
            # Use the jobqueue server if enabled, otherwise run directly
            if botsglobal.ini.getboolean('jobqueue', 'enabled', False):
                # Submit to job queue
                import xmlrpc.client
                jobqueue_host = botsglobal.ini.get('jobqueue', 'host', 'localhost')
                jobqueue_port = botsglobal.ini.getint('jobqueue', 'port', 28082)
                
                # Build the complete command for the job queue
                engine_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'bots-engine.py')
                cmd = [sys.executable, engine_path, route_name]
                
                server = xmlrpc.client.ServerProxy(f'http://{jobqueue_host}:{jobqueue_port}')
                server.addjob(cmd, 1)  # Priority 1
                self.logger.info(f'Scheduler: Route "{route_name}" submitted to job queue')
            else:
                # Run directly
                engine_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'bots-engine.py')
                cmd = [sys.executable, engine_path, route_name]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.logger.info(f'Scheduler: Route "{route_name}" completed successfully')
                else:
                    self.logger.error(f'Scheduler: Route "{route_name}" failed: {result.stderr}')
                    
        except Exception as e:
            self.logger.error(f'Scheduler: Error running route "{route_name}": {str(e)}')
    
    def run_new_messages(self):
        """Run bots-engine with --new flag to process new messages"""
        try:
            self.logger.info('Scheduler: Running new messages processing')
            engine_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'bots-engine.py')
            cmd = [sys.executable, engine_path, '--new']
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info('Scheduler: New messages processing completed')
            else:
                self.logger.error(f'Scheduler: New messages processing failed: {result.stderr}')
        except Exception as e:
            self.logger.error(f'Scheduler: Error in new messages processing: {str(e)}')
    
    def setup_default_schedules(self):
        """Set up default scheduling patterns"""
        # Run new messages every 5 minutes
        schedule.every(5).minutes.do(self.run_new_messages)
        
        # Run automatic retry every hour
        schedule.every().hour.do(self.run_route, '--automaticretrycommunication')
        
        # Run cleanup daily at 2 AM
        schedule.every().day.at("02:00").do(self.run_route, '--cleanup')
        
        self.logger.info('Scheduler: Default schedules configured')
        self.logger.info('  - New messages: every 5 minutes')
        self.logger.info('  - Retry communications: every hour')
        self.logger.info('  - Cleanup: daily at 2:00 AM')
    
    def load_custom_schedules(self):
        """Load custom schedules from database"""
        try:
            # Import Django models
            import django
            from django.conf import settings
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
            if not settings.configured:
                django.setup()
            
            from bots.models import routeschedule
            from datetime import datetime, timedelta
            
            # Clear existing custom schedules (keep defaults)
            # We'll identify custom jobs by checking if they have specific route names
            jobs_to_remove = []
            for job in schedule.jobs:
                job_str = str(job.job_func)
                # Keep default system jobs, remove custom route jobs
                if 'run_route' in job_str and ('--automaticretrycommunication' not in job_str and '--cleanup' not in job_str):
                    jobs_to_remove.append(job)
                elif 'run_custom_route' in job_str:
                    jobs_to_remove.append(job)
            
            for job in jobs_to_remove:
                schedule.cancel_job(job)
            
            # Load active custom schedules from database
            try:
                custom_schedules = routeschedule.objects.filter(active=True)
                loaded_count = 0
                
                for schedule_obj in custom_schedules:
                    try:
                        self.schedule_custom_route(schedule_obj)
                        loaded_count += 1
                        
                        # Update next_run time in database
                        next_run = self.calculate_next_run(schedule_obj)
                        if next_run:
                            schedule_obj.next_run = next_run
                            schedule_obj.save()
                            
                    except Exception as e:
                        self.logger.error(f'Scheduler: Error loading custom schedule "{schedule_obj.name}": {str(e)}')
                
                self.logger.info(f'Scheduler: Loaded {loaded_count} custom schedules from database')
                
            except Exception as e:
                if 'no such table' in str(e).lower():
                    self.logger.info('Scheduler: Custom schedule table not yet created, will be created when first accessed via web interface')
                else:
                    self.logger.error(f'Scheduler: Unexpected error loading custom schedules: {str(e)}')
                self.logger.info('Scheduler: Continuing with default schedules only')
            
        except Exception as e:
            self.logger.error(f'Scheduler: Error loading custom schedules: {str(e)}')
            self.logger.info('Scheduler: Continuing with default schedules only')
    
    def calculate_next_run(self, schedule_obj):
        """Calculate the next run time for a custom schedule"""
        try:
            from datetime import datetime, timedelta
            import schedule as sched_lib
            
            now = datetime.now()
            
            if schedule_obj.frequency == 'minutes':
                return now + timedelta(minutes=schedule_obj.interval)
            elif schedule_obj.frequency == 'hours':
                return now + timedelta(hours=schedule_obj.interval)
            elif schedule_obj.frequency == 'daily':
                if schedule_obj.time_hour is not None:
                    next_run = now.replace(hour=schedule_obj.time_hour, minute=schedule_obj.time_minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    return next_run
                else:
                    return now + timedelta(days=schedule_obj.interval)
            elif schedule_obj.frequency == 'weekly':
                if schedule_obj.weekday and schedule_obj.time_hour is not None:
                    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    target_weekday = weekdays.index(schedule_obj.weekday.lower())
                    days_ahead = target_weekday - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    next_run = now + timedelta(days=days_ahead)
                    next_run = next_run.replace(hour=schedule_obj.time_hour, minute=schedule_obj.time_minute, second=0, microsecond=0)
                    return next_run
                else:
                    return now + timedelta(weeks=schedule_obj.interval)
            elif schedule_obj.frequency == 'monthly':
                if schedule_obj.day_of_month and schedule_obj.time_hour is not None:
                    next_run = now.replace(day=schedule_obj.day_of_month, hour=schedule_obj.time_hour, minute=schedule_obj.time_minute, second=0, microsecond=0)
                    if next_run <= now:
                        # Move to next month
                        if now.month == 12:
                            next_run = next_run.replace(year=now.year + 1, month=1)
                        else:
                            next_run = next_run.replace(month=now.month + 1)
                    return next_run
            
            return None
        except Exception as e:
            self.logger.error(f'Scheduler: Error calculating next run for {schedule_obj.name}: {str(e)}')
            return None
    
    def schedule_custom_route(self, schedule_obj):
        """Add a custom route schedule to the scheduler"""
        try:
            if schedule_obj.frequency == 'minutes':
                schedule.every(schedule_obj.interval).minutes.do(
                    self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                ).tag(f'custom_{schedule_obj.id}')
                
            elif schedule_obj.frequency == 'hours':
                schedule.every(schedule_obj.interval).hours.do(
                    self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                ).tag(f'custom_{schedule_obj.id}')
                
            elif schedule_obj.frequency == 'daily':
                if schedule_obj.time_hour is not None:
                    time_str = f"{schedule_obj.time_hour:02d}:{schedule_obj.time_minute:02d}"
                    schedule.every().day.at(time_str).do(
                        self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                    ).tag(f'custom_{schedule_obj.id}')
                else:
                    schedule.every(schedule_obj.interval).days.do(
                        self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                    ).tag(f'custom_{schedule_obj.id}')
                    
            elif schedule_obj.frequency == 'weekly':
                if schedule_obj.weekday and schedule_obj.time_hour is not None:
                    time_str = f"{schedule_obj.time_hour:02d}:{schedule_obj.time_minute:02d}"
                    getattr(schedule.every(), schedule_obj.weekday.lower()).at(time_str).do(
                        self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                    ).tag(f'custom_{schedule_obj.id}')
                else:
                    schedule.every(schedule_obj.interval).weeks.do(
                        self.run_custom_route, schedule_obj.id, schedule_obj.route_id
                    ).tag(f'custom_{schedule_obj.id}')
            
            self.logger.info(f'Scheduler: Added custom schedule "{schedule_obj.name}" for route "{schedule_obj.route_id}"')
            
        except Exception as e:
            self.logger.error(f'Scheduler: Error scheduling custom route {schedule_obj.name}: {str(e)}')
    
    def run_custom_route(self, schedule_id, route_name):
        """Execute a custom scheduled route and update database"""
        try:
            self.logger.info(f'Scheduler: Running custom scheduled route "{route_name}" (schedule ID: {schedule_id})')
            
            # Run the route
            self.run_route(route_name)
            
            # Update last_run time in database
            try:
                import django
                from django.conf import settings
                from datetime import datetime
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
                if not settings.configured:
                    django.setup()
                
                from bots.models import routeschedule
                schedule_obj = routeschedule.objects.get(id=schedule_id)
                schedule_obj.last_run = datetime.now()
                
                # Calculate and update next run time
                next_run = self.calculate_next_run(schedule_obj)
                if next_run:
                    schedule_obj.next_run = next_run
                
                schedule_obj.save()
                
            except Exception as e:
                self.logger.error(f'Scheduler: Error updating schedule database for ID {schedule_id}: {str(e)}')
                
        except Exception as e:
            self.logger.error(f'Scheduler: Error running custom route {route_name} (schedule ID: {schedule_id}): {str(e)}')
    
    def get_all_schedules(self):
        """Get all schedules from database"""
        try:
            import django
            from django.conf import settings
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
            if not settings.configured:
                django.setup()
            
            from bots.models import routeschedule
            
            schedules = []
            for schedule_obj in routeschedule.objects.all():
                schedules.append({
                    'id': schedule_obj.id,
                    'name': schedule_obj.name,
                    'route_id': schedule_obj.route_id,
                    'active': schedule_obj.active,
                    'frequency': schedule_obj.frequency,
                    'interval': schedule_obj.interval,
                    'time_hour': schedule_obj.time_hour,
                    'time_minute': schedule_obj.time_minute,
                    'weekday': schedule_obj.weekday,
                    'day_of_month': schedule_obj.day_of_month,
                    'last_run': schedule_obj.last_run.isoformat() if schedule_obj.last_run else None,
                    'next_run': schedule_obj.next_run.isoformat() if schedule_obj.next_run else None,
                    'description': schedule_obj.get_schedule_description()
                })
            
            return schedules
            
        except Exception as e:
            self.logger.error(f'Scheduler: Error getting schedules: {str(e)}')
            return []
    
    def create_schedule(self, data):
        """Create a new schedule"""
        try:
            import django
            from django.conf import settings
            from datetime import datetime
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
            if not settings.configured:
                django.setup()
            
            from bots.models import routeschedule
            
            # Create new schedule
            schedule_obj = routeschedule()
            schedule_obj.name = data.get('name', '').strip()
            schedule_obj.route_id = data.get('route_id', '').strip()
            schedule_obj.frequency = data.get('frequency', 'daily')
            schedule_obj.interval = int(data.get('interval', 1))
            schedule_obj.active = data.get('active', True)
            
            if data.get('time_hour'):
                schedule_obj.time_hour = int(data.get('time_hour'))
            if data.get('time_minute'):
                schedule_obj.time_minute = int(data.get('time_minute'))
            if data.get('weekday'):
                schedule_obj.weekday = data.get('weekday')
            if data.get('day_of_month'):
                schedule_obj.day_of_month = int(data.get('day_of_month'))
            
            schedule_obj.enabled_only_weekdays = data.get('enabled_only_weekdays', False)
            schedule_obj.max_retries = int(data.get('max_retries', 3))
            
            # Validate required fields
            if not schedule_obj.name:
                return {"status": "error", "message": "Schedule name is required"}
            if not schedule_obj.route_id:
                return {"status": "error", "message": "Route ID is required"}
            
            schedule_obj.save()
            
            # Reload schedules
            self.load_custom_schedules()
            
            return {"status": "success", "message": f"Schedule '{schedule_obj.name}' created", "id": schedule_obj.id}
            
        except Exception as e:
            self.logger.error(f'Scheduler: Error creating schedule: {str(e)}')
            return {"status": "error", "message": str(e)}
    
    def delete_schedule(self, schedule_id):
        """Delete a schedule"""
        try:
            import django
            from django.conf import settings
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
            if not settings.configured:
                django.setup()
            
            from bots.models import routeschedule
            
            schedule_obj = routeschedule.objects.get(id=schedule_id)
            schedule_name = schedule_obj.name
            schedule_obj.delete()
            
            # Reload schedules
            self.load_custom_schedules()
            
            return {"status": "success", "message": f"Schedule '{schedule_name}' deleted"}
            
        except Exception as e:
            self.logger.error(f'Scheduler: Error deleting schedule: {str(e)}')
            return {"status": "error", "message": str(e)}
    
    def run_scheduler(self):
        """Main scheduler loop"""
        self.logger.info('Scheduler: Starting scheduler loop')
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f'Scheduler: Error in scheduler loop: {str(e)}')
                time.sleep(60)  # Wait longer if there's an error
    
    def start(self):
        """Start the scheduler service"""
        # Set up schedules
        self.setup_default_schedules()
        self.load_custom_schedules()
        
        # Start health check server
        health_server = HTTPServer(('0.0.0.0', 8884), SchedulerHealthHandler)
        health_server.scheduler_instance = self  # Store reference for reload endpoint
        health_thread = threading.Thread(target=health_server.serve_forever, daemon=True)
        health_thread.start()
        self.logger.info('Scheduler: Health check server started on port 8884')
        
        # Start main scheduler
        self.logger.info('Scheduler: Bots EDI Scheduler started')
        self.run_scheduler()

def start():
    """Initialize and start the scheduler"""
    # Initialize bots
    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                configdir = sys.argv[sys.argv.index(arg) + 1]
    
    botsinit.generalinit(configdir)
    
    # Ensure logger is available
    if botsglobal.logger is None:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('bots.scheduler')
    else:
        logger = botsglobal.logger
    
    logger.info('Bots Scheduler starting...')
    
    try:
        scheduler = BotsScheduler()
        scheduler.start()
    except KeyboardInterrupt:
        logger.info('Scheduler: Received interrupt signal, shutting down')
    except Exception as e:
        logger.error(f'Scheduler: Fatal error: {str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    start()