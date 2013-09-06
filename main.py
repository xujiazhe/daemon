#coding=utf8

from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.internet import task

import psutil
import random
import os
import time
import socket
import sys

import config
import path
from   db import DBM_Proxy as dbm
import dispatcher



def is_tornado_service(pid, info):
	'''to verify whether a process is a tornado process we need to monitor
	if it return True, this process start parameters have been saved in dict of info
	'''
    try:    p = psutil.Process(pid)
    except: return False
    runcmd = p.cmdline
    '''try:
        if not p.getcwd().startswith(config.watch_path):
            print "pid = %d " % pid, p.getcwd()
            return False
    except:
            print "pid = try" % pid
            return False
    '''
    if not p.name.endswith('python'):              return False
    if len(runcmd) != config.start_args_len:       return False
    if not runcmd[1].endswith(config.start_file):  return False
    try:
        args = [tuple( e.lstrip('-').split('=') ) for e in runcmd[2:] ]
        argset = set()
        for e in args:
            argset.add(e[0])
            info[e[0]] = e[1]
        assert(argset == set(['db','uname','port']) )
        if not info['db']:
            #p.kill()
            return False
        port_list = [ e[3][1] for e in p.get_connections() ]
        info['port'] = int(info['port'])
        assert( info['port'] in port_list )
        info['process'] = p
        return True
    except Exception,data:
        print "异常",pid,data,type(data)
        return False

def PrintDict(msg, d):
    if not len(d): return
    if not debug:  return
    print msg,len(d)
    for e in d:
        print e,d[e]

class Secretary(object):
	'''
	
	'''
    def __init__(self, addcb, delcb, am = None):
        self.write_watch_stamp()
        self.add_service = addcb
        self.del_service = delcb
        if am is None:
            am = path.AccountMonitor()
        self.am = am

        self.dustbin   = [] # service have been delete
        self.push_list = [] # service to push to dispatcher
        self.wait_list = [] # wait for avaliable db to init

        self.dbm = dbm
        self.__db_state = self.dbm.pull_state()
        self.db2service = dict().fromkeys(config.dbhost_list,[])
        userinfo = am.pull_all_users() #{'xujiazhe': [port, uhome ] }
        PrintDict('userinfo = ', userinfo)
        serviceinfo = self.init_service_from_mem() #{ 'xujiazhe': [pid, port,  db,  process] } 
        PrintDict( 'serviceinfo = ',serviceinfo)
        for uname in serviceinfo:
            sinfo = serviceinfo[uname]
            if uname in userinfo:
                uinfo = userinfo[uname]
                if sinfo[1] == uinfo[0] and self.__db_state[sinfo[2]]:
                    us = UserService(sinfo[0], sinfo[1], sinfo[2], uname, sinfo[3])
                    us.set_errback(self.errback)
                    self.push_list.append( us )
                    self.db2service[sinfo[2]].append(uname)
                    continue
                else:
                    if debug: print "a user's info from am don't stay accord with this from mem_init "
                    if debug: print self
                    uinfo[-1] = uname
                    self.wait_list.append(uinfo)

            us = UserService(sinfo[0], sinfo[1], sinfo[2], uname, sinfo[3])#pid, port, db, name, , pro 
            us.stop()
            self.dustbin.append(us)
        for uname in userinfo:
            if uname not in serviceinfo:
                port = userinfo[uname][0]
                self.wait_list.append( [port, uname] )

        self.add_service(self.push_list,  new = False)
        self.push_list = []

        self.kill_service()
        self.__try_start_service() ## try start service in wait_list

        am.set_callback(self.user_add_handler, self.user_del_handler, \
                            self.user_package_update_handler)

    def set_callback(self, cb, eb):
        self.add_service = cb
        self.del_service = eb

    def write_watch_stamp(self):
        fp = os.path.join( config.watch_path, 'monitor.pid')
        try:
            if os.path.exists( fp ):
                pid = open(fp).readline().strip()
                p = psutil.Process( int(pid) )
                rc = p.cmdline
                if rc[0].endswith('python') and rc[1].endswith(sys.argv[0]):
                    print "path %s have already been watched" % config.watch_path
                    dbm.stop()
                    print "please kill me by hand "
                    sys.exit(1)
            raise Exception("yes you can boy")
        except Exception, e:
            print >> open(fp, "w"), os.getpid()

    def dbchange_handler(self, host, state):
        if self.__db_state[ host ] == state: return

        self.__db_state[ host ] = state
        print "*"*50
        print 'here dbchange_handler ', host, state
        if state:
            if self.wait_list:
                self.__try_start_service(host)
        else:
            d2s = self.db2service[host]
            for i in range(len(d2s)-1,-1,-1):
                L = [0]
                si = self.del_service(d2s[i], L)
                si = si or L[0]

                si.stop()
                self.dustbin.append(si)
                d2s.pop(i)
                self.wait_list.append( [si.port, si.name] )
            self.__try_start_service()


    def init_service_from_mem(self):
        serviceinfo = {}
        for pid in psutil.get_pid_list():
            pinfo = {}
            if not is_tornado_service(pid, pinfo):
                continue
            port = pinfo['port']
            db = pinfo['db']
            uname = pinfo['uname']
            process = pinfo['process']
            serviceinfo[uname] = [pid, port, db, process]
        return serviceinfo

    def kill_service(self):
        if not self.dustbin:return
        for i in range(len(self.dustbin)-1,-1,-1):
            if self.dustbin[i].is_alive():
                print "弄不死" ,self.dustbin[i]
                self.dustbin[i].stop()
            else:
                self.dustbin.pop(i)

    def __try_start_service(self, host = ''):
        if host:
            dblist = [host]*len(self.wait_list)
        else:
            dblist = dbm.get_alive_db_list(len(self.wait_list))
            print len(self.wait_list)

        if dblist:
            if debug: print self.wait_list
            if debug: print dblist
            for i in range(len(dblist)):
                uinfo = self.wait_list[i]
                us = UserService(0, uinfo[0], dblist[i], uinfo[-1])
                us.set_errback(self.errback)
                self.db2service[dblist[i]].append(uinfo[-1])####
                self.push_list.append(us)
            self.wait_list = []
            self.add_service(self.push_list, new = True)
            self.push_list = []

    def user_package_update_handler(self, uname):
        L = [0]
        si = self.del_service(uname, L)
        si = si or L[0]
        port = si.port
        si.stop()
        self.dustbin.append(si)
        self.wait_list.append( [port, uname] )
        self.__try_start_service()


    def user_add_handler(self, uinfo):
        #print "!!!添加了用户"
        pstr = ''
        for e in uinfo:
            pstr += "\t"+str(uinfo[e])
        else:
            if debug: print pstr
        uname = uinfo['uname']
        port = uinfo['port']
        self.wait_list.append([port, uname])
        self.__try_start_service()

    def user_del_handler(self, uname):
        if debug: print "!!!!用户%s的信息已经被删除" % uname
        L = [0]
        si = self.del_service(uname, L)
        si = si or L[0]
        si.stop()
        self.dustbin.append(si)
    
    def errback(self, uname):
        L = [0]
        si = self.del_service(uname, L)
        si = si or L[0]
        
        si.stop()
        self.dustbin.append(si)
        self.wait_list.append( [si.port, si.name] )
        self.__try_start_service()

    def new_task(self, si):
        url = 'http://localhost:%d/runinfo' % si.port
        if debug: print "任务已经分配" ,url
        def justtest(body, arg):
            print arg
            print 'in justtest ',body

        def another_test(err, arg):
            print arg
            print 'err back',err

        getPage(url).addCallbacks( si.http_valid_verify, si.http_errback);  return
        getPage(url).addCallbacks( justtest, another_test,['test'], errbackArgs = ['test1']);  return


class UserService:
    '''	each tornado process(or those processes that will be start) conrrespond to an instance of UserService	'''
    def __init__(self, pid, port, db, name, pro = None):
        ''' construct a instance of user's tornado web service
		pid could be 0, which means this instance need a start operation
		or if pid is not 0 there must be alive process in memory, in that case pro couldn't be None
        '''
        self.pid = pid
        self.port = port
        self.db = db
        self.name = name
        self.ts = time.time()
        self.home = os.path.join( config.watch_path, name, "")
        if pid == 0:
            self.pro = None
            self.start() #it will update his own pid attribute
            return
        self.pro = pro; assert( pro != None )

        if os.path.isdir( self.home ) and self.home_info_verify(): pass
        else:
            print "some error , user service init failed",self
            self.stop()
    def set_time(self, ts = 0):
        self.ts = ts

    def set_errback(self, errback):
        self.errback = errback

    def home_info_verify(self):
        self.start_file = os.path.join(self.home, config.start_file)
        if os.path.isfile( self.start_file ) == False:
            return False
        try:
            portf = os.path.join(self.home ,'port')
            pidf  = os.path.join(self.home ,'pid')
            port = int( open(portf).readline().strip() )
            if port != self.port:
                raise Exception("port is not consistent")
            pid = int( open(pidf).readline().strip() )
            if pid != self.pid:
                raise Exception("self.pid couldn't agree with the res grasp from web ??")
            return True
        except Exception,data:
            print 'data = ',data
            return False

    def update_pid_from_home(self):
        fn = os.path.join(self.home, 'pid')
        if debug: print self,"更新pid"
        try:
            strpid = open(fn).readline().strip()
            if debug: print '1'
            pid = int(strpid)
            if debug: print '2'
            if debug: print self.pid, pid
            self.pid = pid
            if debug: print '3'
            self.pro = psutil.Process(pid)
            if debug: print '4'
            
            return True
        except Exception,data:
            print self,' home update failed '
            print data
            return False

    def start(self):
        if self.is_alive() == True:
            print "没事瞎忙活"
            return
        self.pro = None
        self.pid = 0
        #start_command = 'cd %s; python %s --db=%s --port=%s --uname=%s 1>>out 2>>err &'
        cmd = config.start_command % (self.home, config.start_file,\
                    self.db, self.port, self.name)
        self.start_time = time.time()
        code = os.system(cmd)
        if code:
            print "%s's start meet pro!!! " % self.name

    def stop(self):
        print 'try stop ',self
        if self.is_alive() == False: return
        self.pro.kill()
        try: self.pro.terminate()
        except:pass
        #self.boss.remove_service(self.name)

    def restart(self, changedb = ''):

        def test_port_available(port):
            socked_var = socket.socket()
            assert(isinstance(port, int))
            try:
                socked_var.bind( ('localhost', port) )
                socked_var.close()
                return True
            except:
                return False
        print self,'重启'

        if changedb and self.db != changedb:
            self.db = changedb
        if self.is_alive():
            self.pro.kill()
        self.start() ##may be it couldn't start up, because the port recycle are limited by system setting
    def http_errback(self, err):
        print self,'errors occur when asynchronously fetch http results  ',err
        self.errback(self.name)
        #self.restart()

    def http_valid_verify(self, res):
        #192.168.2.31|8888|3993|test
        print res,' already return '
        r = res.split('|')
        if len(r) != 4:
            self.errback(self.name)

        wport = int(r[1])
        if wport != self.port:
            print "this is fucking impossible  ",self
            return
        wpid = int(r[2])
        if wpid != self.pid:
            print "wpid = ",wpid
            print 'self.pid = ',self.pid

            print"web验证有点不正常" ,self
            self.pid = wpid
            self.pro = psutil.Process( wpid )
        if r[3] != self.name:
            print"Name inconsistencies" ,self
        print "pass the verification  ",self
        self.set_time(0)

    def is_alive(self):
        if self.pro is None: return False
        return self.pro.is_running()

    def __repr__(self):
        return "service %s port(%d) pid(%d) db(%s) " % (self.name, self.port, self.pid, self.db)


debug = False
path.debug = False
#db.debug = False
dispatcher.debug = False

if __name__ == "__main__":
    Dict = {}
    def Add(push_list,  new = False):
        for si in push_list:
            print "add user %s" % si.name
            Dict[ si.name ] = si
        print "total %d " % len(Dict)

    def Del(uname):
        si = Dict[uname]
        del Dict[uname]
        print "del user %s" % si.name
        print "total %d " % len(Dict)
        return si
    #s = Secretary(Add, Del)
    
    ds = dispatcher.ServiceDispatcher(config.url_check_effective_period)
    s = Secretary(ds.add_service_callback, ds.del_service_callback )
    ds.set_main(s)

task.LoopingCall( s.kill_service ).start(config.url_check_effective_period)
reactor.run()
print 'over here' * 4
