#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import time
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import xmlrpc.client as xmlrpclib
from xmlrpc.server import SimpleXMLRPCServer

from . import botsinit
from . import botslib
from . import botsglobal

PRIORITY = 0
JOBNUMBER = 1
TASK = 2
start_time = time.time()

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            uptime = time.time() - start_time
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()
            self.wfile.write(f"OK - uptime={uptime:.2f}s\n".encode())
        else:
            self.send_error(404)
            
def health():
    # For XMLRPC
    uptime = time.time() - start_time
    return {"status": "OK", "uptime": uptime}

class Jobqueue(object):
    def __init__(self,logger):
        self.jobqueue = []
        self.jobcounter = 0
        self.logger = logger

    def addjob(self,task,priority):
        for job in self.jobqueue:
            if job[TASK] == task:
                if job[PRIORITY] != priority:
                    job[PRIORITY] = priority
                    self.logger.info('Duplicate job, changed priority to %(priority)s: %(task)s',{'priority':priority,'task':task})
                    self._sort()
                    return 0
                else:
                    self.logger.info('Duplicate job not added: %(task)s',{'task':task})
                    return 4
        self.jobcounter += 1
        self.jobqueue.append([priority, self.jobcounter, task])
        self.logger.info('Added job %(job)s, priority %(priority)s: %(task)s',{'job':self.jobcounter,'priority':priority,'task':task})
        self._sort()
        return 0

    def clearjobq(self):
        del self.jobqueue[:]
        self.logger.info('Job queue cleared.')
        return 0

    def getjob(self):
        if len(self.jobqueue):
            return self.jobqueue.pop()
        return 0

    def _sort(self):
        self.jobqueue.sort(reverse=True)
        self.logger.debug('Job queue changed. New queue: %(queue)s',{'queue':''.join(['\n    ' + repr(job) for job in self.jobqueue])})


def action_when_time_out(logger,maxruntime,jobnumber,task_to_run):
    logger.error('Job %(job)s exceeded maxruntime of %(maxruntime)s minutes',{'job':jobnumber,'maxruntime':maxruntime})
    botslib.sendbotserrorreport('[Bots Job Queue] - Job exceeded maximum runtime',
                                'Job %(job)s exceeded maxruntime of %(maxruntime)s minutes:\n %(task)s' % {
                                    'job':jobnumber,'maxruntime':maxruntime,'task':task_to_run
                                })

def launcher(logger,port,lauchfrequency,maxruntime):
    print(f"DEBUG: Launcher function started with port={port}, freq={lauchfrequency}")
    DEVNULL = open(os.devnull, 'wb')
    print(f"DEBUG: Creating XML-RPC client to localhost:{port}")
    xmlrpcclient = xmlrpclib.ServerProxy('http://localhost:' + str(port))
    maxseconds = maxruntime * 60
    print("DEBUG: Sleeping 3 seconds before starting launcher loop...")
    time.sleep(3)
    print("DEBUG: Starting launcher main loop...")
    nr_runs_NOK = 0
    while True:
        try:
            time.sleep(lauchfrequency)
            job = xmlrpcclient.getjob()
            if job:
                priority, jobnumber, task_to_run = job
                logger.info('Starting job %(job)s',{'job':jobnumber})
                starttime = time.time()
                process = subprocess.Popen(task_to_run, stdout=DEVNULL, stderr=DEVNULL)
                timer = threading.Timer(maxseconds, action_when_time_out,
                                        args=(logger, maxruntime, jobnumber, task_to_run))
                timer.start()
                result = process.wait()
                timer.cancel()
                time_taken = time.time() - starttime
                logger.info('Finished job %(job)s, elapsed time %(time_taken)s, result %(result)s',
                            {'job':jobnumber,'time_taken':time_taken,'result':result})
                nr_runs_NOK = 0
        except Exception as msg:
            nr_runs_NOK += 1
            logger.error('Error occured in the bots-jobqueueserver: %(msg)s',{'msg':msg})
            botslib.sendbotserrorreport('[Bots Job Queue] Error in bots-jobqueueserver',
                                        'An error occured in the bots-jobqueueserver: %(msg)s' % {'msg':msg})
            if nr_runs_NOK >= 10:
                logger.error('More than 10 consecutive errors in the bots-jobqueueserver, shutting down now')
                botslib.sendbotserrorreport('[Bots Job Queue] bots-jobqueueserver has stopped',
                                            'More than 10 consecutive errors occured in the bots-jobqueueserver, so jobqueue-server is stopped now.')
                sys.exit(1)

def start():
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    Server program that ensures only a single bots-engine runs at any time, and no engine run requests are
    lost/discarded. Each request goes to a queue and is run in sequence when the previous run completes.
    Use of the job queue is optional and must be configured in bots.ini (jobqueue section, enabled = True).
    Usage:
        %(name)s  -c<directory>
    Options:
        -c<directory>   directory for configuration files (default: config).
    ''' % {'name':os.path.basename(sys.argv[0]), 'version':botsglobal.version}

    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print('Error: configuration directory indicated, but no directory name.')
                sys.exit(1)
        else:
            print(usage)
            sys.exit(0)
    botsinit.generalinit(configdir)
    if not botsglobal.ini.getboolean('jobqueue','enabled',False):
        print('Error: bots jobqueue cannot start; not enabled in %s/bots.ini' % configdir)
        sys.exit(1)

    process_name = 'jobqueue'
    logger = botsinit.initserverlogging(process_name)
    logger.log(25, 'Bots %(process_name)s started.', {'process_name':process_name})
    logger.log(25, 'Bots %(process_name)s configdir: "%(configdir)s".',
                {'process_name':process_name, 'configdir':botsglobal.ini.get('directories','config')})

    port = botsglobal.ini.getint('jobqueue','port',28082)
    logger.log(25, 'Bots %(process_name)s listens for xmlrpc at port: "%(port)s".',
                {'process_name':process_name,'port':port})

    print("DEBUG: Getting launcher configuration...")
    lauchfrequency = botsglobal.ini.getint('jobqueue','lauchfrequency',5)
    maxruntime = botsglobal.ini.getint('settings','maxruntime',60)
    print(f"DEBUG: Config loaded - freq={lauchfrequency}, maxruntime={maxruntime}")

    print(f"DEBUG: About to create launcher thread with port={port}, freq={lauchfrequency}, maxruntime={maxruntime}")
    launcher_thread = threading.Thread(name='launcher', target=launcher,
                                       args=(logger, port, lauchfrequency, maxruntime))
    launcher_thread.daemon = True
    print("DEBUG: Starting launcher thread...")
    launcher_thread.start()
    print("DEBUG: Launcher thread started, logging message...")
    logger.info('Jobqueue launcher started.')
    
    print("DEBUG: About to log server started message...")
    logger.info('Jobqueue server started.')
    print("DEBUG: Starting HTTP health server...")
    
    threading.Thread(
        target=HTTPServer(('0.0.0.0', 8882), HealthCheckHandler).serve_forever,
        daemon=True
    ).start()
    
    server = SimpleXMLRPCServer(('0.0.0.0', port), logRequests=False)
    server.register_instance(Jobqueue(logger))
    server.register_function(health, 'health')
    
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    sys.exit(0)

if __name__ == '__main__':
    start()
