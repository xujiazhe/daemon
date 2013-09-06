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
