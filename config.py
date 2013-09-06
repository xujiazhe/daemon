#coding=utf8
'''
If the configuration file (passed in from the command parameters, or assigned "tornadod.conf" by default) exists, default configure value will be updated
'''
import ConfigParser
from optparse import OptionParser
import os

configfile = 'tornadod.conf'

USAGE = "usage: %prog [-???]  [-c configfile] arg"
Parser = OptionParser(USAGE)
Parser.add_option("-c", default = configfile, 
							action = "store", type = "string",
							dest = "configfile", help = "read config from config file")

Parser.add_option("-f", "--file", action = "store", 
							type = "string", dest = "filename")

#modified_effect_on_time = True

url_check_effective_period = 10
start_time = 1
http_verify_timeout = 1

dbhost_list = ['192.168.2.31', '192.168.2.33', '192.168.2.34']
username = 'xf'
password = '123456'
database = 'ccc'
dbstate_update_rate = 8
connect_timeout = 5

watch_path = '/home/xujiazhe/test'

start_file = 'tornado_test.py'
start_command = 'cd %s; python %s --db=%s --port=%s --uname=%s 1>>out 2>>err &'
start_args_len = 5

def read_config_file():
    '''configure from config file, value read from configure file will
       substitude the default value set above
    '''
    global modified_effect_on_time, url_check_effective_period, start_time,\
        dbhost_list, username, password, database, dbstate_update_rate,\
        connect_timeout, watch_path, start_file, start_command, start_args_len, \
        http_verify_timeout

    if not os.path.exists(configfile):
        print "配置文件不存在", configfile
        return

    cf = ConfigParser.ConfigParser()
    cf.read(configfile)

    #[daemon]
    modified_effect_on_time = cf.getboolean("daemon","modified_effect_on_time")
    #[dispatcher]
    url_check_effective_period = cf.getint("dispatcher","url_check_effective_period")
    start_time = cf.getint("dispatcher","start_time")
    http_verify_timeout = cf.getint("dispatcher","http_verify_timeout")

    #[database]
    dl = cf.get('database','dbhost_list')
    dbhost_list = [e.strip() for e in dl.split(',')]
    username = cf.get('database','username')
    password = cf.get('database','password')
    database = cf.get('database','database')
    dbstate_update_rate = cf.getint('database','dbstate_update_rate')
    connect_timeout = cf.getint('database','connect_timeout')
    
    #[account]
    watch_path = cf.get('account','watch_path')
    
    #[service]
    start_file = cf.get('service','start_file')
    start_command = cf.get('service','start_command')
    start_args_len = cf.getint('service','start_args_len')

#args = ["-f", "foo.txt",'-c','tornadod.conf','xujiazhe']
#(options, args) = Parser.parse_args(sys.argv)
(options, args) = Parser.parse_args()

configfile = options.configfile
read_config_file()

def read_cmd():
    '''args
    '''
    pass

assert( start_time < url_check_effective_period )

if __name__ == '__main__':
    import MySQLdb
    for d in dbhost_list:
        print 'dbhost test = ', d
        try:
            con = MySQLdb.connect(host = d, user = username,\
                   passwd = password, db = database, connect_timeout = connect_timeout) ## timeout
            print 'great  ',con
            con.close()
        except: 
            print "youwenti", d
