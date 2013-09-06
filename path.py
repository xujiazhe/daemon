#coding=utf8
import os
import time
import copy
import threading
import config

import asyncore
import pyinotify

'''
When you want to add a user, add directory under the monitored directory folder. 
	the new added directory's name should be same as that user's name
	add port files and Tornado start package should be place under that directory
this module's function is mainly to report the messages of appearence, disapearence and modification of effective user


The effective user should meet those conditions
Folder name see as the user name
Add clip below the symbol
there should exist those file
	A file named port, inside which lay a port number which is assigned to this user. it should be same with other effective users
				or the information of the one whose port file add later couldn't be add and push
	Tornado start package, with this package, you can start this user's tornado process; the start file is config.start_file

we use pyinotify module
'''

def portrange(port):
    if 0 < port < 65535:return True
    return False

debug = False
debug = True

class UserInfoChangeHandler(pyinotify.ProcessEvent):
	'''Monitor and push message of change of the valid user, it save all valid users' info in user_dict and port_dict
	support command of  mv cp rm mkdir touch and so on
	'''
    def __init__(self, add_callback=None,del_callback=None):
        self.path = os.path.join(config.watch_path,"")
        self.user_dict = {}
        self.port_dict = {}
        self.init_all_users()
        self.premod = []
        self.add_callback = add_callback
        self.del_callback = del_callback

    def set_add_callback(self, add_callback):
        self.add_callback = add_callback
    def set_del_callback(self, del_callback):
        self.del_callback = del_callback
    def set_upd_callback(self, upd_callback):
        self.upd_callback = upd_callback

    def pull_all_users(self):
        return copy.deepcopy(self.user_dict)
        
    def init_all_users(self):
        '''scanf the path, and init all users info
        '''
        dl = os.listdir(self.path)

        for uname in dl:
            info = {}
            if self.is_valid_user(uname, info):
                port = info['port']
                self.user_dict[ uname ] = [ port, self.get_user_home(uname) ]
                self.port_dict[ port ] = [ info['time'], uname ]

    def is_valid_user(self, uname, info = None):
        '''if there are valid port file and startfile under dpath return its port
            otherwise, 0 will be returned
        '''
        userpath = self.get_user_home( uname )
        if not userpath:   return False
        port_file = os.path.join(userpath, 'port')
        sfe = os.path.isfile( os.path.join(userpath, config.start_file) )
        rie = os.path.isfile( port_file )

        if not sfe or not rie: return False
        strport = open(port_file).readline().strip()
        if not strport.isdigit():return False
        port = int(strport)
        if not portrange(port):return False
        ct = os.stat(port_file).st_ctime
        if port in self.port_dict: #port重复
            if self.port_dict[port][1] == uname:pass
            else:
                print '！！！端口重复！！！ %s with %s' % (uname, self.port_dict[port][1])
                if self.port_dict[port][0] < ct:
                    return False
                else:###覆盖？？？ 通知吗？
                    self.user_dict.pop( self.port_dict[port][1] )
        if info is None:
            return True
        info['port'] = port
        info['time'] = ct
        info['uname'] = uname
        return True

    def get_username(self, event):
        pathname = event.pathname
        if not pathname.startswith(self.path):
            return ''
        ul = pathname[ len(self.path): ].split(os.sep,2)
        if len(ul) == 3: return ''#用户目录下的文件(夹)的改变不影响他的信息的有效性
        if len(ul) == 2 and event.dir: return ''

        uname = ul[0]

        if uname.startswith('.'):   return ''
        if os.path.isdir( self.get_user_home( uname ) ) or event.dir:
            return uname
        else:
            return ''

    def process_IN_CREATE(self, event):
        if debug: print " CREATE: %s "  %  event.pathname
        uname = self.get_username( event )
        if not uname: return
        if uname in self.user_dict:
            #这里可能更新软件包
            uh = self.get_user_home( uname )
            startfile = os.path.join( uh, config.start_file )
            if event.pathname == startfile:
                #self.upd_callback(uname)
                pass
            return
        else:
            info = {}
            if self.is_valid_user(uname, info):
                port = info['port']
                ct   = info['time']
                self.user_dict[uname] = [ port, os.path.join(self.path, uname)]
                self.port_dict[port] = [ ct, uname ]
                print "添加了新用户 %s " % uname
                if self.add_callback:
                    self.add_callback(info)
                else: print "没有回调函数 将被忽略"
                return

    def process_IN_DELETE(self, event):
        if debug: print "文件被删除:", event.pathname#，文件被删除，如 rm
        uname = self.get_username( event )
        if not uname: return
        print "uname = ",uname
        if uname in self.user_dict:
            if not self.is_valid_user(uname):
                port = self.user_dict[uname][0]
                self.user_dict.pop(uname)
                self.port_dict.pop(port)
                print "删除了用户 %s" % uname
                if self.del_callback:
                    self.del_callback(uname)
                else:  print "没有del回调函数 将被忽略"

    def process_IN_MODIFY(self, event):
        this = [event.pathname,round(time.time(), 2)]
        if self.premod == this: return
        if debug: print   "*********文件被修改 ", event.pathname #，如 IN_MODIFY
        self.premod = this
        uname = self.get_username( event )
        if not uname: return
        info = {}
        if self.is_valid_user(uname, info):
            port = info['port']
            ct   = info['time']
            if uname in self.user_dict:
                if self.user_dict[uname][0] != port:
                    print "修改了用户的端口 你妹！"
                else:
                    self.port_dict[port][0] = ct
                    return
                #这里可能更新软件包
                uh = self.get_user_home( uname )
                startfile = os.path.join( uh, config.start_file )
                if event.pathname == startfile:
                    #self.upd_callback(uname)
                    pass
                return
            self.user_dict[uname] = [ port, os.path.join(self.path, uname)]
            self.port_dict[port] = [ ct, uname ]
            #self.callback('所有的用户', self.user_dict)#####################
        elif uname in self.user_dict:
            print "修改用户信息致使用户失效"
            port = self.user_dict[uname][0]
            self.user_dict.pop(uname)
            self.port_dict.pop(port)
            if self.del_callback:
                self.del_callback(uname)#####################
            else: print "没有del回调函数 将被忽略"

    def process_IN_MOVED_TO(self, event):
        uname = self.get_username( event )
        if not uname: return
        if uname in self.user_dict:return
        info = {}
        if self.is_valid_user(uname, info):
            port = info['port']
            ct   = info['time']
            self.user_dict[uname] = [ port, os.path.join(self.path, uname)]
            self.port_dict[port] = [ ct, uname ]
            print "移动添加了新用户 %s " % uname
            if self.add_callback: self.add_callback(info)
            else: print "没有回调函数 将被忽略"
        if debug: print "文件被移来:", event.pathname#，文件被移来，如 mv、cp

    def process_IN_ATTRIB(self, event):
        uname = self.get_username( event )
        if not uname: return
        if not event.dir: return
        if debug: print "文件属性被修改:", event.pathname
        info = {}
        is_user = self.is_valid_user(uname, info)

        if uname in self.user_dict:
            if not is_user:
                port = self.user_dict[uname][0]
                self.user_dict.pop(uname)
                self.port_dict.pop(port)
                print "删除了新用户 %s " % uname
                if self.del_callback:self.del_callback(uname)#####################
                else: print "没有del回调函数 将被忽略"
        elif is_user:
            port = info['port']
            ct   = info['time']
            self.user_dict[uname] = [ port, self.get_user_home(uname) ]
            self.port_dict[port] = [ ct, uname ]
            print "添加了新用户 %s " % uname
            if self.add_callback:self.add_callback(info)
            else: print "没有add回调函数 将被忽略"
            
    def get_user_home(self, uname):
        userpath = os.path.join( self.path, uname )
        if os.path.isdir(userpath):   return userpath
        return ''

    def process_IN_MOVED_FROM(self, event):
        uname = self.get_username( event )
        if not uname: return
        if uname in self.user_dict:
            if not self.is_valid_user(uname):
                print "移动删除了用户 %s" % uname
                port = self.user_dict[uname][0]
                self.user_dict.pop(uname)
                self.port_dict.pop(port)
                if self.del_callback:self.del_callback(uname)#####################
                else: print "没有del回调函数 将被忽略"
        if debug: print "文件被移走:", event.pathname#，文件被移走,如 mv
    #def process_IN_UNMOUNT(self, event):
    #    print "主文件系统被:umount", event.pathname#，宿主文件系统被 umount

class AccountMonitor(threading.Thread):
    def __init__(self, addcb = None, delcb = None, updcb = None):
        threading.Thread.__init__( self )
        self.EventHandler = UserInfoChangeHandler()
        self.EventHandler.set_add_callback(addcb)
        self.EventHandler.set_del_callback(delcb)
        self.EventHandler.set_upd_callback(updcb)

        wm = pyinotify.WatchManager()
        mask =  pyinotify.IN_DELETE | pyinotify.IN_MODIFY   | pyinotify.IN_CREATE |\
            pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | pyinotify.IN_ISDIR  |\
            pyinotify.IN_ATTRIB
            
        notifier = pyinotify.AsyncNotifier(wm, self.EventHandler)
        wdd = wm.add_watch(config.watch_path, mask, rec=True, auto_add = True)
        #self.setDaemon(True)
        self.start()
    def set_callback(self, addcb = None, delcb = None, updcb = None):
        self.EventHandler.set_add_callback(addcb)
        self.EventHandler.set_del_callback(delcb)
        self.EventHandler.set_upd_callback(updcb)
    def pull_all_users(self):
        return self.EventHandler.pull_all_users()
    def run(self):
        #help(asyncore)
        asyncore.loop()



if __name__ == "__main__":
    def printdict(msg,d):

        print "%s size %d" % (msg, len(d))
        for e in d:
            print e, d[e]
        print "%s size %d " % (msg,len(d))
    class test():
        def __init__(self):
            self.x = 10
        def setA(self, A):
            self.A = A
        def Del(self, uname):
            print "用户%s的信息已经被删除" % uname
            d = self.A.pull_all_users()
            printdict('删除后', d)
            print '*'*30
        def Add(self, d):
            print "添加了用户"
            pstr = ''
            for e in d:
                pstr += "\t"+str(d[e])
            else:  print pstr
            d = self.A.pull_all_users()
            printdict('增加后', d)
            print '*'*30
        def show(self):
            print "hrereererererrrer"
    
    t = test()
    #a = UserInfoChangeHandler('/home/xujiazhe/test', )
    c = AccountMonitor(t.Add, t.Del)
    t.setA(c)
    u = c.pull_all_users()
    for e in u:
        print e , u[e]
    #p = a.port_dict
    #print "*"*40
    #printdict("所有用户",u) 
    #printdict("所有端口",p)
    #print "*"*40
    

# name="test"
# mkdir $name  && cp tornado_test.py $name/ && echo "8888" > $name/port
