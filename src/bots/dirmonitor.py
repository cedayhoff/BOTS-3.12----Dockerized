#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import fnmatch
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# Bots modules
from . import botsinit
from . import botsglobal
from . import job2queue

start_time = time.time()

'''
monitors directories for new files.
if a new file, lauch a job to the jobqueue server (so: jobqueue-server is needed).
directories to wachs are in config/bots.ini
runs as a daemon/service.
this module contains separate implementations for linux and windows
'''

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
            
if os.name == 'nt':
    try:
        import win32file, win32con
    except Exception as msg:
        raise ImportError('Dependency failure: bots directory monitoring requires python library "Python Win32 Extensions" on windows.')

    def windows_event_handler(logger,dir_watch,cond,tasks):
        ACTIONS = { 1 : 'Created  ',      #tekst for printing results
                    2 : 'Deleted  ',
                    3 : 'Updated  ',
                    4 : 'Rename from',
                    5 : 'Rename to',
                    }
        FILE_LIST_DIRECTORY = 0x0001
        hDir = win32file.CreateFile(dir_watch['path'],           #path to directory
                                    FILE_LIST_DIRECTORY,          #access (read/write) mode
                                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,  #share mode: FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                                    None,                         #security descriptor
                                    win32con.OPEN_EXISTING,       #how to create
                                    win32con.FILE_FLAG_BACKUP_SEMANTICS,    # file attributes: FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED
                                    None,
                                    )
        # detecting right events is not easy in windows :-(
        # want to detect: new file,  move, drop, rename, write/append to file
        # only FILE_NOTIFY_CHANGE_LAST_WRITE: copy yes, no move
        # for rec=True: event that subdirectory itself is updated (for file deletes in dir)
        while True:
            results = win32file.ReadDirectoryChangesW(  hDir,
                                                        8192,                   #buffer size was 1024, do not want to miss anything
                                                        dir_watch['rec'],       #recursive
                                                        win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_SIZE |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_SECURITY |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_CREATION |       #unknown, does not work!
                                                        #~ win32con.FILE_NOTIFsY_CHANGE_LAST_ACCESS |   #unknown, does not work!
                                                        win32con.FILE_NOTIFY_CHANGE_LAST_WRITE,
                                                        None,
                                                        None
                                                        )
            if results:
                #for each incoming event: place route to run in a set. Main thread takes action.
                for action, filename in results:
                    logger.debug('Event: %(action)s %(filename)s',{'action':ACTIONS.get(action,'Unknown'),'filename':filename})
                for action, filename in results:
                    if action in [1,3,5] and fnmatch.fnmatch(filename, dir_watch['filemask']):
                        #~ if dir_watch['rec'] and os.sep in filename:
                            #~ continue
                        #~ full_filename = os.path.join (path_to_watch, file)
                        cond.acquire()
                        tasks.add(dir_watch['route'])
                        cond.notify()
                        cond.release()
                        break       #the route is triggered, do not need to trigger more often
    #end of windows-specific ##################################################################################
else:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class LinuxEventHandler(FileSystemEventHandler):
        def __init__(self, logger, dir_watch_data, cond, tasks):
            super().__init__()
            self.logger = logger
            self.dir_watch_data = dir_watch_data
            self.cond = cond
            self.tasks = tasks

        def on_created(self, event):
            self._handle_any(event)

        def on_moved(self, event):
            self._handle_any(event)

        def on_modified(self, event):
            self._handle_any(event)

        def _handle_any(self, event):
            # event.src_path = full path
            # event.is_directory = bool
            if event.is_directory:
                return
            base_name = os.path.basename(event.src_path)
            for dir_watch in self.dir_watch_data:
                if event.src_path.startswith(dir_watch['path']):
                    if fnmatch.fnmatch(base_name, dir_watch['filemask']):
                        self.cond.acquire()
                        self.tasks.add(dir_watch['route'])
                        self.cond.notify()
                        self.cond.release()

    def linux_event_handler(logger, dir_watch_data, cond, tasks):
        observer = Observer()
        handler = LinuxEventHandler(logger, dir_watch_data, cond, tasks)
        for dw in dir_watch_data:
            observer.schedule(handler, dw['path'], recursive=dw['rec'])
        observer.start()
        try:
            observer.join()
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    #end of linux-specific ##################################################################################


def start():
    #NOTE: bots directory should always be on PYTHONPATH - otherwise it will not start.
    #***command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    A utility to generate the index file of a plugin; this can be seen as a database dump of the configuration.
    This is eg useful for version control.
    Usage:
        %(name)s  -c<directory>
    Options:
        -c<directory>   directory for configuration files (default: config).

    '''%{'name':os.path.basename(sys.argv[0]),'version':botsglobal.version}
    threading.Thread(
        target=HTTPServer(('0.0.0.0', 8888), HealthCheckHandler).serve_forever,
        daemon=True
    ).start()
        
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
    #***end handling command line arguments**************************
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.
    if not botsglobal.ini.getboolean('jobqueue','enabled',False):
        print('Error: bots jobqueue cannot start; not enabled in %s/bots.ini'%(configdir))
        sys.exit(1)
    process_name = 'dirmonitor'
    logger = botsinit.initserverlogging(process_name)
    logger = botsinit.initserverlogging('dirmonitor')
    botsenginepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'bots-engine.py')
    cond = threading.Condition()
    tasks = set()
    dir_watch_data = []
    for section in botsglobal.ini.sections():
        if section.startswith('dirmonitor') and section[len('dirmonitor'):]:
            watch_path = botsglobal.ini.get(section,'path')
            print("DEBUG: watch_path is", watch_path)
            dir_watch_data.append({})
            dir_watch_data[-1]['path'] = botsglobal.ini.get(section,'path')
            dir_watch_data[-1]['rec'] = botsglobal.ini.getboolean(section,'recursive',False)
            dir_watch_data[-1]['filemask'] = botsglobal.ini.get(section,'filemask','*')
            dir_watch_data[-1]['route'] = botsglobal.ini.get(section,'route','')
    if not dir_watch_data:
        logger.error('Nothing to watch!')
        sys.exit(0)

    if os.name == 'nt':
         #for windows: start a thread per directory watcher
        for dir_watch in dir_watch_data:
            dir_watch_thread = threading.Thread(target=windows_event_handler, args=(logger,dir_watch,cond,tasks))
            dir_watch_thread.daemon = True  #do not wait for thread when exiting
            dir_watch_thread.start()
    else:
        watch_thread = threading.Thread(target=linux_event_handler,
                                        args=(logger, dir_watch_data, cond, tasks))
        watch_thread.daemon = True
        watch_thread.start()

    # this main thread get the results from the watch-thread(s).
    logger.info('Bots %(process_name)s started.',{'process_name':process_name})
    active_receiving = False
    timeout = 2.0
    cond.acquire()
    while True:
        #this functions as a buffer: all events go into set tasks.
        #the tasks are fired to jobqueue after TIMOUT sec.
        #this is to avoid firing to many tasks to jobqueue; events typically come in bursts.
        #is value of timeout is larger, reaction times are slower...but less tasks are fired to jobqueue.
        #in itself this is not a problem, as jobqueue will alos discard duplicate jobs.
        #2 sec seems to e a good value: reasonable quick, not to nervous.
        cond.wait(timeout=timeout)    #get back when results, or after timeout sec
        if tasks:
            if not active_receiving:    #first request (after tasks have been  fired, or startup of dirmonitor)
                active_receiving = True
                last_time = time.time()
            else:     #active receiving events
                current_time = time.time()
                if current_time - last_time >= timeout:  #cond.wait returned probably because of a timeout
                    try:
                        for task in tasks:
                            logger.info('Send to queue "%(path)s %(config)s %(task)s".',{'path':botsenginepath,'config':'-c' + configdir,'task':task})
                            job2queue.send_job_to_jobqueue([sys.executable,botsenginepath,'-c' + configdir,task])
                    except Exception as msg:
                        logger.info('Error in running task: "%(msg)s".',{'msg':msg})
                    tasks.clear()
                    active_receiving = False
                else:                                   #cond.wait returned probably because of a timeout
                    logger.debug('time difference to small.')
                    last_time = current_time
    cond.release()
    sys.exit(0)


if __name__ == '__main__':
    start()
