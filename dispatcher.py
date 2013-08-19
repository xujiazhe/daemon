#coding=utf8
import threading
import psutil
import time
import sys
import config
import os

from mycollections import OrderedDict

def TS(s = 0):
    if not s: s = time.time()
    return time.strftime("%H:%M:%S", time.localtime( s ) )

debug = False
debug = True

_condition = threading.Condition()

def synchronized(func):
    def wrapper(*args, **kwargs):
        _condition.acquire()
        try:
            func(*args, **kwargs)
        finally:
            _condition.release()

    wrapper.func_name = func.func_name
    wrapper.__doc__ = func.__doc__
    return wrapper

class ServiceDispatcher(threading.Thread):
    def __init__(self, valid_period, main = None):
        threading.Thread.__init__( self, name = 'great')
        if main:
            self.main = main
            main.set_callback( self.add_service_callback, self.del_service_callback)

        self._valid  = OrderedDict(expire_time = \
            config.url_check_effective_period - config.http_verify_timeout)
        self._verify = OrderedDict(expire_time = config.http_verify_timeout)
        self._start  = OrderedDict(expire_time = config.start_time)

        self._valid_period = valid_period
        self.start()

    def set_main(self, main):
        self.main = main
        main.set_callback( self.add_service_callback, self.del_service_callback)


    @synchronized
    def add_service_callback(self, servicelist, new = True):
        for si in servicelist:
            if new:
                self._start.prepend(si)
            else:
                self._valid.append(si)
                self._valid[si.name].si.set_time( ts = 1 ) #it will put into verify list imdiately

    @synchronized
    def del_service_callback(self, uname, L):## return si
        print "shanchu ",uname
        if uname in self._valid:
            si = self._valid.pop(uname)
            L[0] = si
            print '_valid',si
            return si
        elif uname in self._verify:
            si = self._verify.pop(uname)
            L[0] = si
            print '_valid',si
            return si
        elif uname in self._start:
            si = self._start.pop(uname)
            L[0] = si
            print '_valid',si
            return si
        else:
            print "err in dispatcher del_service_callback"

    @synchronized
    def run(self):
        while 1:
            if debug:
                print "dispatcher one round ", len(self._valid),len(self._verify),len(self._start)

            while len(self._start) and self._start.have_invalid():
                #if debug: print 'start dispatch',self
                res = self._start.last().si.update_pid_from_home()
                #if debug: print self._start.last()._uname
                si = self._start.popitem()
                if res:
                    self._valid.append(si)
                    self._valid[si.name].si.set_time( ts = 1 )
                else:
                    print si,'重启失败'
                    si.restart()
                    self._start[si.name] = si

            while len(self._valid) and self._valid.have_invalid():
                print 'valid 2 verify dispatch',self
                si = self._valid.popitem()
                self._verify[si.name] = si
                self.main.new_task( si )

            while len(self._verify) and  self._verify.have_invalid():
                print 'verify 2 start dispatch',self
                si = self._verify.popitem()
                if si.ts == 0:
                    self._valid[si.name] = si
                else:
                    si.restart()
                    self._start[si.name] = si

            wait_time1 = self._valid_period
            wait_time2 = config.start_time

            if len(self._valid):
                wait_time1 = time.time() + self._valid_period - self._valid.last().si.ts
            if len(self._verify):
                wait_time2 = time.time() + config.connect_timeout - self._verify.last().si.ts
            wait_time = min(wait_time1, wait_time2)
            # wait util last node in valid_list or verify_list need care, or the lost watch_dog return
            _condition.wait(wait_time)
    def __repr__(self):
        s = "Dispatcher list\n"
        s += 'valid  ' + ' '.join( ['.' + uname for uname in self._valid]  ) + '\n'
        s += 'verify ' + ' '.join( ['?' + uname for uname in self._verify] ) + '\n'
        s += 'start  ' + ' '.join( ['!' + uname for uname in self._start]  ) + '\n'
        return s

if __name__ == '__main__':
    def PrintChange(host, state, d):
        print 'X'*40
        s =  TS(), "%s's state changed into %s" % (host, str(state))
        a = d.items()
        s1 = '\t'   +  '\t'.join([e[0] for e in a])
        s2 = '\t\t' +  '\t\t'.join([str(int(e[1])) for e in a])
        print  s
        print  s1
        print  s2

    #DB_Master  hostlist, valid_period, commit_change_func=None
    valid_period = 2
    hostlist = ['172.16.239.94',  '172.16.239.52', '172.16.239.93']
    #dbm = db.DB_Master(hostlist, valid_period, PrintChange) 
    sd = ServiceDispatcher( valid_period )
    #a = dbm.pull_state()
    #print time.time(), a

    #print time.time(), dbm.pull_state()
#设置 valid_period = 2 connection_timeout=2
#封14:00  反应过来
#封05:50  1:40反应过来
#封01:00  0:40反应过来
#封00:04  0:02反应过来
