Monitoring and Management System of FMCG Invoicing Service

Invoicing project select the tornado as its Web server and nginx reverse proxy. One tornado process serves one user.
From the browser, mobile terminal, the FMCG Invoicing project provides professional online invoicing management services.
During running of tornado service process, many possible exceptions may occur such as process crashes, DB status changing to (un)available, the tornado process get stuck, daemon crash itself. 
And there also may come some daily routine, such as Add-Del-Modify a user's information, tornado application package update, update the daemon configuration file. 
Daemon will handle all of these events in real-time at minimal performance cost to ensure stability and robustness of invoicing service.
The system is divided into several modules
	Main modules:
		receiving and processing the incident pushed over from other modules.
	User information module:
		all users' configure information and service start files would be put under certain path. This module will monitor change(add-mod-Del) of the user information, and push message of adduser, deluser, moduser to the main module.
	Database connection module:
		report the status change of dbs to main module. Harmonious code, graceful process, beautiful as sexy girl's long legs
	User Service availability checking module:
		operate dispatch queue, and assign service availability  check tasks to main module


项目背景：      在线进销存管理系统中，每一个商户对应其中一个web服务进程，每个web服务进程只连接同步数据库中的一个。通过监控管理服务进程，db，用户信息和web服务软件升级包的变化，开发了该deamon系统，确保了服务的鲁棒性实时性。
使用技术：     linux环境，nginx网页代理服务器，tornado web服务器，语言为python, shell。
完成模块介绍：
db模块：每个监控狗负责监控检查一个db连接，db主任来给他们分配检查任务，根据提交情况更改一个db状态表。外部模块通过db代理来访问,重启db主任，db主任通过代理向外推送db的变化。
path模块:在用户目录下放着用户的配置信息，当增删改这些信息的时候，该模块向主模块提交变化。
dispatcher：负责对这些web服务进行周期性检查，
主模块：负责对各种变化消息做出应对，当然它也会保证重启有效性。
测试程序：模拟服务中各种突发事件，然后观察该deamon应对情况。

未完成模块：
  软件包的升级，当软件包升级的时候，付费用户应该更新。(该模块需要和web服务软件包开发人员协定)
  该daemon应该注册到linux系统服务中去，这样daemon挂掉也会被重启。(linux有现成的这样的东西，需要查找测试一下。)

现存问题：
端口平静时间，大多数高并发web程序都会遇到的问题，已通过系统设置TCP参数解决。
需要这样一种数据结构，先进先出，查找删除快速，链表用hash索引一下可以满足这样的需求(mycollections.py)，python库中的orderdict应该是哈希索引的数组——查找删除不给力。

inotify是接受文件(目录)变化消息通知的linux API, pyinotify是用python封装的这写API。
测试显示，当用批处理更改文件的时候，pyinotify消息推送有时会卡顿，但不会漏报。 
这个时候需要刷新一下文件目录消息还是会被推出来的。也就是在通过批处理改动用户信息的时候，如果没有生效，刷新一下那个目录。
