**Monitoring and Management System of FMCG online Invoicing Service**
**快销品在线进销存服务管理系统**
====
**used technologies**:  Linux environment, nginx web reverse proxy, tornado web server, develop language: Python, Shell. 
Invoicing project select the tornado as its Web server and nginx reverse proxy. One tornado process serves one user; programming language: python, shell

**使用技术**：     linux环境，nginx网页代理服务器，tornado web服务器，语言为python, shell。
****

##Project Background:
From the browser, mobile terminal, the FMCG Invoicing project provides professional online invoicing management services.

In invoicing project, One tornado process serves one company(user). Each service process would connect to one of multi-synchronized databases. During service processes' running, many exceptions may occur such as process crashes, DB status changing to (un)available, the tornado process get stuck, daemon crash itself. 

And there also may come some daily routines, such as Add-Del-Modify a user's information, tornado application package update, update the daemon configuration file. 

This daemon will monitor and handle all of these events in real-time at minimal performance cost, to ensure stability and robustness of invoicing service

在线进销存管理系统中，一个tornado进程服务与一个商户，每个服务进程只连接多同步db数据库中的一个。在服务运行中,很多异常可能发生比如db不可用了,进程卡死了,也有可能进行一些日常事务比如增删用户,程序包更新等等. 由此就需要一个就需要一个监控处理这些事件和变化的程序来保证在线服务的鲁棒性实时性.
    

##  Modules Instruction：


- **Main module:**

    Each module will push some message to this module, main module will react properly on each kind of message. Of course it will also ensure its validation after a restart.

    主模块：负责对各种模块推送过来的变化消息做出应对，当然它也会保证自己的重启有效性。

- **DB module:**

    Each Connection_watch_dog is responsible for watching and checking a certain db connection. the db_master will assign checking task with a deadline to them. after deadline db_master will look through who haven't report, and change a dict of dbs status. Outside module could visit, restart db_master through this proxy, and massage of db change could be push out through this proxy too.

    每个监控狗负责监控检查一个db连接，db主任来给他们分配检查任务，根据提交情况更改一个db状态表。外部模块通过db代理来访问,重启db主任，db主任通过代理向外推送db的变化。

- **Path module:**

    user's personnel directory(under which lie that user's config and running service pid file and using port info) will be put under specified path, when some modification, addition and deletion of these personnel information occur under that path. message of adduser, deluser, moduser to the main module.

    path模块:在用户个人目录下放着用户的配置信息服务进程pid,和port端口，当在那个目录下增删改这些信息的时候，该模块向主模块提交变化消息。

- **Dispatcher module:**

    It's responsible for checking those web processes' validation cyclically.

    负责对这些web服务进行周期性检查，有三个调度状态队列.

- **Test module:**

    模拟服务中各种突发事件，然后观察该deamon应对情况。

    Simulate most kinds of incidents and daily routine in service running, such as
        process crashes, DB status changing to (un)available, the tornado process get stuck, daemon crash itself.

    and  Add-Del-Modify a user's information, tornado application package update, update the daemon configuration file.

    then see the handling and recovery result of this daemon.
[框架图](框架图.png)

###Existing problems：
    pyinotify massage push need manually flush: Inotify is a series of API for receiving change massage of specified file and fold. python library of pyinotify is just a  encapsulation of these API. when I use bat to change users' directory(it happen quickly), pyinotify's massage pushing sometime get a little stuck. but not miss any massage, for which I only need to manually flush that fold. 

    inotify是接受文件(目录)变化消息通知的linux API, pyinotify是用python封装的这写API。

    测试显示，当用批处理更改文件的时候，pyinotify消息推送有时会卡顿，但不会漏报。 

    这个时候需要刷新一下文件目录消息还是会被推出来的。也就是在通过批处理改动用户信息的时候，如果没有生效，刷新一下那个目录。
