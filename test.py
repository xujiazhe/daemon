
class A(object):
    freelist = A.malloc()
    def __init__(self):
        print ("__init__")
    @static
    def malloc():
        A.freelist = 1

    

    def __new__(self):
        print ("__new__")


A()


