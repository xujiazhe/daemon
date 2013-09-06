#2#coding=utf8
import threading
import MySQLdb
import time
import random
import math
import sys
import config

def TS(s = 0):
    if not s: s = time.time()
    return time.strftime("%H:%M:%S", time.localtime( s ) )

debug = True
debug = False

class Connection_Watch_Dog(threading.Thread):
    """Accepts the task from DB_Master  (to verify the state of DB connection it holds itself, which can cause network IO stuck),
    and report state to DB_Master before deadline as possible 
    """
    def __init__(self, host, connect_timeout, master, init = True):
        if debug: print >> sys.stderr, '#1'
        if init:
            threading.Thread.__init__(self, name = 'watch dog thread of host %s' % host)
            if debug: print >> sys.stderr, '#2'
        else:
            threading.Thread.__init__(self)
            if debug: print >> sys.stderr, '#3'
        self.__task_command = threading.BoundedSemaphore(1)
        if debug: print >> sys.stderr, '#4'
        self.__host = host		# (str) ip of db_host
        self.__con = None		# connection instance of MySQLdb
        self.__task_deadline = None  # (float) 
        self.__state = False
        self.__ct = connect_timeout
        self.submit_callback = master.submit_callback
        self.return_callback = master.dog_return_callback
        self.init_callback   = master.init_callback
        self.__keep_go = True
        self.__task_command.acquire()
        self.init = init
        self.setDaemon(True)
        self.start()

    def set_task(self, deadline):
        self.__task_deadline = deadline
        if debug:
			print TS(), 'set task ', self
        self.__task_command.release()

    def set_state(self, state):
        self.__state = state

    def init_connection(self):
        try:
            con = MySQLdb.connect(host=self.__host, user=config.username, \
                    passwd=config.password, db=config.database, \
                    connect_timeout=self.__ct)
            self.__con   = con
            self.__state = True
        except Exception, data:
            print >> sys.stderr, 'init connect failed ', data

        self.init_callback(self.__host, self.__state)

    def __docheck(self):

        if self.__state:
            #verify the connection
            if debug: print TS(), "%s try show stat " % self.__host
            try:
                if self.__con.stat() == 'MySQL server has gone away':
                    self.__state = False
            except:
                self.__state = False
        elif self.__con is None:
            if debug:
                print "连接 " * 20
                print "%s try connect %s" % (self.__host, TS(time.time()) )
            try:
                con_timelimit = int( math.ceil( self.__task_deadline - time.time() ) )
                con = MySQLdb.connect(host=self.__host, user=config.username, \
                      passwd=config.password, db=config.database, connect_timeout=con_timelimit)

                self.__state = True
                self.__con   = con
            except Exception, data:
                if debug:
                    print TS(), "这里 connect failed %s " % self.__host
                    print 'data = ', data
        else:
            self.__con.close()
            self.__con = None
            if debug: print "%s try connect %s" % (self.__host, TS(time.time()) )
            try:
                con_timelimit = math.ceil( self.__task_deadline - time.time() )

                con = MySQLdb.connect(host=self.__host, user=config.username, \
                    passwd=config.password, db=config.database, connect_timeout=con_timelimit)

                self.__state = True
                self.__con = con
            except Exception, data:
                if debug: print TS(), "这里 connect failed %s " % self.__host

    def run(self):
        if self.init: self.init_connection()
        while self.__keep_go:
            self.__task_command.acquire()	#wait for the task
            deadline = self.__task_deadline	#get the deadline of task
            self.__docheck()                #perform task, may get stuck in this function
            assert( self.__keep_go )
            if deadline >= time.time():		#if get the task done within deadline
                self.submit_callback(self.__host, self.__state)
            else:										#
                self.__state = False
                self.return_callback(self.__host)

    def __repr__(self):
        s =  'host(%s) state(%s) deadline(%s)' % (self.__host, \
                    str(self.__state), TS(self.__task_deadline) )
        if self.__host == '172.16.239.93':
            s += str(self.__con)
        return s

    def stop(self):
        '''this function mainly used in expirelist'''
        print "in stop ", self.__con
        self.__keep_go = False
        self.return_callback = None
        self.submit_callback = None
        self.init_callback = None
        try:  self.__con.close()
        except: pass

    def __del__(self):
        self.return_callback = None
        self.__keep_go = False
        self.submit_callback = None
        self.init_callback = None
        try:  self.__con.close()
        except: pass

class DB_Master(threading.Thread):
    """	Controlling several Connection_Watch_Dog classes, maintain three scheduling queue
		According to schedule steps, assigned task to Connection_Watch_Dog and
		accepting their reporting information through submit_callback
    """
    class ele(object):
		'''	element nodes in schedual queue	'''
        def __init__(self, host, ts = time.time()):
            self.next = None
            self.pre = None
            self.host = host	#db host
            self.time = ts		#timestamp, in different queue it has different mean

        def set_value(self, host, ts = time.time()):
            self.host = host
            self.time = ts
            return self

        def __eq__(self, host):
            return self.host == host
        def __hash__(self):
            return hash(self.host)
        def __repr__(self):
            return "<%s>ele object host(%s) %s" % (__name__ , self.host, TS(self.time) )
        def __str__(self):
            return "<%s>ele object host(%s) %s" % (__name__ , self.host, TS(self.time) )

    def __init__(self, hostlist, valid_period, dbchange_handler=None, init = True):
		'''
		hostlist is list of db which should be
        valid_period is validity period of a db connection, after such period of time, the state of this connection
            should be verify again
        dbchange_handler deal the event that the state of db connection change, 
		'''
        threading.Thread.__init__(self)
        self.__valid_head  = None
        self.__verify_head = None
        self.__expire_head = None

        self.__verify_dict = {}
        self.__expire_dict = {}

        self.__calloc( len(hostlist) )
        self.valid_len = 0

        self.valid_period = valid_period
        self.hostlist = hostlist
        self.__db_state = dict.fromkeys( hostlist, False)

        #if you wanna to change the ring, acquire it first
        self.__condition = threading.Condition()
        self.__pull_able = threading.Event()
        self.__pull_able.clear()
        self.dbchange_callback = dbchange_handler
        self.init = init
        self.db_dogs = {}
        for h in hostlist:
            self.db_dogs[h] = Connection_Watch_Dog(h, config.connect_timeout, self)
        self.__keep_go = True
        if __name__ != '__main__':
            self.setDaemon(True)
        self.start()

    def set_callback(self, callback):
        self.dbchange_callback = callback

    def __calloc(self, length):
        self.freelist = None
        self.left = length
        for i in range(length):
            e = self.ele('None')
            e.next = self.freelist
            self.freelist = e
    def __malloc(self):
        assert(self.left > 0)
        e = self.freelist
        self.freelist = self.freelist.next
        self.left -= 1
        return e

    def __free(self, e):
        print 'test  ', e
        e.pre  = None
        e.next = self.freelist
        self.freelist = e
        self.left += 1

    def __preppend2valid(self, e):
        #if debug: print "before preppend ", self
        #if debug: print 'e = ',e
        if self.__valid_head is None:
            e.pre = e.next = e
            self.__valid_head = e
            self.__verify_head = self.__expire_head = e
        else:
            e.next = self.__valid_head
            e.pre = self.__valid_head.pre
            self.__valid_head.pre = e
            e.pre.next = e

            self.__valid_head = e
            if self.__expire_empty():
                self.__expire_head = self.__valid_head
                if self.__verify_empty():
                    self.__verify_head = self.__expire_head
        self.valid_len += 1
        if debug: print "after preppend valid ", self


    def __append2valid(self, e):
        #if debug: print "before append ", self
        #if debug: print 'e = ',e
        if self.__valid_head is None:
            self.__valid_head = e
            e.pre = e.next = e
            self.__verify_head = self.__expire_head = e
        else:
            e.next = self.__verify_head
            e.pre  = self.__verify_head.pre
            self.__verify_head.pre = e
            e.pre.next = e
            if self.__valid_empty():
                self.__valid_head = e
                if self.__expire_empty():
                    self.__expire_head = self.__valid_head
        self.valid_len += 1
        if debug: print "after append ", self

    def init_callback(self, host, state, ts = time.time()):
        e = self.__malloc()
        e.set_value(host, ts)
        self.__db_state[ host ] = state
        self.__preppend2valid(e)
        if state and not self.init:
            self.__push_state(host, state)
        if self.left == 0:
            self.__pull_able.set()

    def dog_return_callback(self, host):
        #if debug: print "before return %s " % host, self
        if host not in self.__expire_dict:
            print " %s not in expire_dict" % host
            print self
            return 
        self.__condition.acquire()
        e = self.__expire_delete(host)
        self.__append2valid(e)
        self.__condition.notify()#notify the master's thread
        self.__condition.release()
        if debug: print "after return %s " % host, self

    def submit_callback(self, host, state):
        #if debug: print "before submit  %s %s" % (host,str(state)), self
        push_record = False
        self.__condition.acquire()
        if self.__db_state[host] != state:
            self.__db_state[host] = state
            push_record = True
        e = self.__verify_delete(host)
        e.time = time.time()
        self.__preppend2valid(e)
        self.__condition.release()
        if push_record:
            self.__push_state(host, state)
        if debug: print "after submit %s " % host, self

    def __valid_empty(self):
        return self.valid_len == 0
    def __valid_last(self):
        return self.__verify_head.pre
    def __valid2verify(self):
        #if debug: print "before v2v ", self
        change = False
        while not self.__valid_empty():
            if self.__valid_last().time < time.time()-self.valid_period:
                change = True
                self.__verify_head = self.__verify_head.pre
                self.__verify_head.time = time.time()
                self.__verify_dict[ self.__verify_head.host ] = self.__verify_head
                self.valid_len -= 1
                self.db_dogs[ self.__verify_head.host ].set_task\
                                (time.time() + config.connect_timeout)
            else:  break
        else:
            if change: print "after v2v ", self

    def __verify_empty(self):
        return len(self.__verify_dict)==0
    def __verify_last(self):
        return self.__expire_head.pre
    def __verify_delete(self, host):
        e = self.__verify_dict[host]
        self.__verify_dict.pop(host)
        e.pre.next = e.next
        e.next.pre = e.pre

        if e.next == e:
            self.__valid_head = self.__verify_head = self.__expire_head = None
            e.next = e.pre = None
            return e
        if self.__verify_head == e:
            self.__verify_head = e.next
            if self.__valid_empty():
                self.__valid_head = self.__verify_head
                if self.__expire_empty():
                    self.__expire_head = self.__valid_head
        e.pre = e.next = None
        return e

    def __verify2expire(self):
        #if debug: print "before v2e ", self
        change = False
        while not self.__verify_empty():
            if self.__verify_last().time < time.time()-config.connect_timeout:
                self.__expire_head = self.__expire_head.pre
                self.__expire_dict[ self.__expire_head.host ] = self.__expire_head
                self.__verify_dict.pop(self.__expire_head.host)
                host = self.__expire_head.host
                if self.__db_state[ host ]:
                    self.__db_state[ host ] = False
                    self.changedict[host] = False
                change = True
            else: break
        else:
            if change:  print "after v2e ", self

    def __expire_empty(self):
        return len(self.__expire_dict) == 0
    def __expire_delete(self, host):
        e = self.__expire_dict[host]
        print "in __expire_delete ", host
        print host in self.__expire_dict
        print "in __expire_delete ", e

        self.__expire_dict.pop(host)
        e.pre.next = e.next
        e.next.pre = e.pre
        e.time = 1
        if e.next == e:
            self.__valid_head = self.__verify_head = self.__expire_head = None
            e.next = e.pre = None
            return e

        if self.__expire_head == e:
            self.__expire_head = e.next
            if self.__verify_empty():
                self.__verify_head = self.__expire_head
                if self.__valid_empty():
                    self.__valid_head = self.__expire_head
        e.pre = e.next = None
        return e

    def pull_state(self, timeout=0):
        if timeout==0:
            self.__pull_able.wait()###test it !!!
        else:
            self.__pull_able.wait(timeout)###test it !!!
        return self.__db_state

    def __push_state(self, host, state):
        if not self.dbchange_callback:
            return
        self.dbchange_callback(host, state, self.__db_state)

    def need_restart(self):
        if len(self.hostlist)*[False] != self.__db_state.values():
            return False
        if self.__expire_empty():
            return False

    def get_alive_db_list(self, length):
        ''' randomly generate a list of length number of connectable db if there exist any available(alive)
            otherwise return []; 
            #but will envoke(only once) callback when there comes an available db
        '''
        def get_alive_db_list(dbstate):
            m = -1
            random_alive_one = ''
            for db in dbstate:
                if dbstate[db]:
                    k = random.random()
                    if k > m:
                        m = k
                        random_alive_one = db
            if random_alive_one:  return random_alive_one
            else: return ''
        res = []
        if length > 1 and len(self.__db_state) > 1:
            tlist = []
            for db in self.__db_state:
                if self.__db_state[db]: tlist.append(db)
            if not tlist:
                return res
            ci = 0
            for i in xrange(length):
                print "great"
                ri = random.randint(0,len(tlist))
                ci = (ci + ri) % len(tlist)
                res.append( tlist[ci] )
            return res
        for i in range(length):
            alive_one = get_alive_db_list( self.__db_state )
            if not alive_one:
                return []
            res.append(alive_one)
        return res
    def stop(self):
        self.__keep_go = False
        self.__condition.acquire()
        self.__condition.notifyAll()
        self.__condition.release()

    def restart(self):
        '''When there's no DB available, probably because DB_Connection_Dogs' running thread block in network IO (in function of con.stat),
		if it get block there, it would be in expire_list
		this function returns a new DBM
        '''
        #if all their state are false and expire not empty
        if not self.need_restart():
            return self

        self.__keep_go = False
        self.__condition.acquire()
        self.__condition.notifyAll()
        self.__condition.release()
        new_dbm = DB_Master(self.hostlist, self.valid_period, \
                        self.dbchange_callback, init = False) 
        return new_dbm
        
        '''the following is old code, will not be run'''
        if self.__expire_empty(): return
        self.__condition.acquire()
        self.__pull_able.clear()
        while not self.__expire_empty():
            host = self.__valid_head.pre.host
            self.db_dogs[host].stop()
            e = self.__expire_delete(host)
            self.__free(e)
            self.db_dogs[host] = Connection_Watch_Dog(host, config.connect_timeout, self, init = False)

        self.__condition.release()

    def run(self):
        self.__pull_able.wait()
        self.__condition.acquire()
        while self.__keep_go:
            self.changedict = {}
            self.__valid2verify()
            self.__verify2expire()
            
            for k in self.changedict:
                self.__push_state(k, self.changedict[k])
            wait_time1 = self.valid_period
            wait_time2 = config.connect_timeout
            now_time = time.time()
            if not self.__valid_empty():
                wait_time1 = now_time + self.valid_period - self.__valid_last().time
            if not self.__verify_empty():
                wait_time2 = now_time + config.connect_timeout - self.__verify_last().time
            wait_time = min(wait_time1, wait_time2)
            # wait util last node in valid_list or verify_list need care, or the lost watch_dog return
            #if debug:
            #    print "in master thread "
            #    print self.db_dogs[ '172.16.239.93' ]
            self.__condition.wait(wait_time)
        self.__condition.release()

    def __repr__(self):
        s = TS() + ' DB_Master thread %d %d %d' % (self.valid_len, len(self.__verify_dict), len(self.__expire_dict))
        e = self.__valid_head
        length = self.valid_len + len(self.__verify_dict) + len(self.__expire_dict)
        while e and length:
            length -= 1
            delimeter = ' '
            if e.host in self.__verify_dict:
                delimeter = '?'
                if e.host in self.__expire_dict:
                    delimeter+= '!X'
            elif  e.host in self.__expire_dict: delimeter = '!'
            s += '\n\t'+delimeter+str(e)
            e = e.next
        s += '\n'
        return s


def PrintChange(host, state, d):
        s =  TS(), "%s's state changed into %s" % (host, str(state))
        a = d.items()
        s1 = '\t'   +  '\t'.join([e[0] for e in a])
        s2 = '\t\t' +  '\t\t'.join([str(int(e[1])) for e in a])
        #f = open("data","a")
        #f = sys.stdout
        print  s
        print  s1
        print  s2


#class Singleton(object):
#    _instance

# singleton & proxy
class DBM_Proxy(object):
    '''DBM_Proxy is proxy of DB_Master instance. it initialize a DB_Master with the configure
	callback is a function to be invoked when state of DB connection changed
	flush would be executed when there is no available DB and there block some db_connection in network IO in expire list
	pull_state's function is pulling all the state of DBs
    '''
    _this_dbm_proxy = DB_Master(config.dbhost_list, config.dbstate_update_rate) 
    __init__ = None
    ts = time.time()
    #__new__  = None
    @staticmethod
    def set_callback(callback):
        DBM_Proxy._this_dbm_proxy.set_callback( callback )

    @staticmethod
    def flush():
        '''	only when no DB is available	'''
        #control the flush frequency
        if time.time() - DBM_Proxy.ts < 2:
            print "不要刷新太频繁"
            return
        DBM_Proxy.ts = time.time()
        DBM_Proxy._this_dbm_proxy = DBM_Proxy._this_dbm_proxy.restart()

    @staticmethod
    def get_alive_db_list(length):
        res = DBM_Proxy._this_dbm_proxy.get_alive_db_list(length)
        if res:return res
        if DBM_Proxy._this_dbm_proxy.need_restart():
            DBM_Proxy.flush()
    @staticmethod
    def pull_state():
        '''you may meet a little block at start or just after flush'''
        return DBM_Proxy._this_dbm_proxy.pull_state()
    @staticmethod
    def stop():
        DBM_Proxy._this_dbm_proxy.stop()
    #def __new__(cls, *args, **kwargs):
    #    if not cls._this_dbm_proxy:
    #        cls._this_dbm_proxy = super(DBM_Proxy, cls).__new(
    #                                cls, *args, **kwargs)
    #    return cls._this_dbm_proxy

if __name__ == '__main__':
    DBM_Proxy.set_callback(PrintChange)
    a = DBM_Proxy.pull_state()
    print a
    #print time.time(), dbm.pull_state()
    #设置 valid_period = 2 connection_timeout=2
    #封14:00  反应过来
    #封05:50  1:40反应过来
    #封01:00  0:40反应过来
    #封00:04  0:02反应过来

