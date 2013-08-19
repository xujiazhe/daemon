# encoding: UTF-8
import time

'''
这个OrderedDict仅插入和弹出比库里面的那个快将近4倍  果断用这个了
'''
class OrderedDictIterator(object):
    def __init__(self, tar):
        self.start = tar.top()
        self.stop  = tar.last()
        self.cur = self.start
        self.tag = self.start
    def next(self):
        if self.cur == self.stop:
            raise StopIteration
        if self.tag != self.cur:
            self.cur = self.tag
        self.tag = self.cur._next
        return self.cur._uname

class OrderedDict(object):
    class ele(object):
        '''the instance of ele, could put in linklist, and be index by hashtable in OrderedDict
            si is abre of  tornado service instance
        '''
        _freelist = None
        _left_size = 0
        def __init__(self, si):
            self._prev  = None
            self._next = None
            self._uname = ''
            self.si = si
            #si.set_time(time.time())
            #self.db = ''
            
        def set_value(self, si):
            self.si = si
            self._uname = si.name
            si.set_time(time.time())
            #self.db = si.db
            return self
        #def __new__(self ):
        #    if not ele._freelist:
                
        def invalid(self, expire_time):
            return time.time() > self.si.ts + expire_time
        def __eq__(self, data):
            return self._uname == data
        def __hash__(self):
            return hash(self._uname)
        def __repr__(self):
            return "<%s>ele object uname=" % __name__ + str(self._uname)

    class linkedlist(object):
        '''仅仅是对双链表的操作'''
        def __init__(self):
            self._head = None
            self._tail = None
        def prepend(self, e):
            if self._tail is None:
                self._head = self._tail = e
                e._prev = e._next = None
                return
            e._next = self._head
            self._head._prev = e
            e._prev = None

            self._head = e
            return e
        def append(self, e):
            if self._head is None:
                self._head = self._tail = e
                e._prev = e._next = None
                return
            self._tail._next = e
            e._prev = self._tail
            e._next = None
            self._tail = e
        def popitem(self, e = None):# e is None,pop the last one
            if not e:   e = self._tail
            #print "*" * 20
            #print e
            #print e._prev,e._next
            #print "*" * 20
            if e._prev: e._prev._next = e._next
            else:       self._head = e._next
            if e._next: e._next._prev = e._prev
            else:       self._tail = e._prev
            e._prev = e._next = None
            return e

        def top(self):
            return self._head
        def last(self):
            return self._tail

        def empty(self):
            return self._head is None
        def __repr__(self):
            e = self._head
            s = 'dlink'
            while e:
                s += ' -> %s' % str(e.uname)
                e = e._next
            return s
        def __str__(self):
            return self.__repr__()

    def __init__(self, expire_time = 2, size = 500):
        self.hashtable = dict()
        self.link = self.linkedlist()
        self.freenode = None
        self.__hash__ = None
        self.expire_time = expire_time
        for i in range(size):
            t = self.ele(None)
            t._next = self.freenode
            self.freenode = t
    def __malloc(self):
        assert(self.freenode != None)
        e = self.freenode
        self.freenode = e._next
        e._next = None
        return e
    def __free(self, e):
        e._next = self.freenode
        self.freenode = e
    #def invalid(self, expire_time = self.expire_time):

    def size(self):
        return len(self.hashtable)
    def top(self):
        if self.size():
            return self.link.top()
        return None
    def last(self):
        if self.size():
            return self.link.last()
        return None

    def have_invalid(self):
        return time.time() > self.last().si.ts + self.expire_time

    def popitem(self, last = True):
        return self.deque()
    def append(self, si):
        e = self.__malloc().set_value(si)
        self.hashtable[e] = e
        self.link.append(e)
    def prepend(self, si):
        e = self.__malloc().set_value(si)
        self.hashtable[e] = e
        self.link.append(e)###

    def deque(self):
        e = self.link.popitem()
        self.hashtable.pop(e)
        self.__free(e)
        return e.si

    def pop(self, uname):
        assert( uname in self.hashtable )
        e = self.hashtable.pop(uname)
        self.link.popitem( e )
        si = e.si
        self.__free(e)
        print 'in pop',si
        return si
        
    def __delitem__(self, uname):
        e = self.hashtable.pop(uname)
        self.link.popitem( e )
        self.__free(e)
    def __setitem__(self, uname, si):
        e = self.__malloc().set_value(si)
        self.hashtable[uname] = e
        self.link.prepend(e)

    def __getitem__(self, uname):
        return self.hashtable[uname]
    def __contains__(self, uname):
        return uname in self.hashtable
    def __len__(self):
        return len(self.hashtable)
    def __iter__(self):
        return OrderedDictIterator(self)
    def __repr__(self):
        s = str(len(self.hashtable))
        s += str(self.link)
        return s

#进si出si
#访问返回e

if __name__ == '__main__':

    class service_instance(object):
        def __init__(self, uname, ts = time.time() ):
            self.name = uname
            self.ts = time.time()
        def set_time(self, ts = 0):
            self.ts = ts

    s = time.time()
    UPLIMIT = 500
    a = OrderedDict(UPLIMIT)
    for i in range(UPLIMIT):
        si = service_instance('test%04d'%i )
        a[ si.name ] = si
    
    for uname in a:
        print uname
    
    print len(a)
    print time.time() -s 
    
