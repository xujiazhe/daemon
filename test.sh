#!/bin/bash
#sudo bash test.sh &>/home/xujiazhe/WK/test.log  &
#run under the main.py monitor path
#at first the path should have no user;

MONITOR_PID_FILE="monitor.pid"

USER_LIMIT=10
users=()
ports=()
dbhosts=(172.16.239.93 172.16.239.52 172.16.239.94) #172.16.239.94 172.16.239.93 172.16.239.52)
deluser=()
delport=()
lock_recode=(1 1 1)

LASTROUND_CHECK_RES=0
ROUND_TIME=10

_log(){
   echo -e 1>&2 `date +%H:%M:%S`"\t"$@
}

function finddb()
{
    dbhost=$1
    for (( i = 0 ; i < ${#dbhosts[@]} ; i++ ))
    do
        if [ "$dbhost" = "${dbhosts[$i]}" ] ;
        then
            echo $i;return 0;
        fi
    done
    _log ${dbhosts[@]} , '\n\tfind ',$dbhost ,'error'
    echo -1
    return 1
}

function get_port()
{
    #port between 1025 ~ 65535
    port=$(($RANDOM%(65535-1024)+1024+1))
    status=$(./available_test $port)

    if [ $status != $port ] ;then
        tvar=$(get_port)
        echo $tvar
        return $tvar
    fi
    
    for(( i=0;i<${#ports[@]};i++))
    {
        if [ ${ports[$i]} = "$port" ];then
            tvar=$(get_port)
            echo $tvar
            return $tvar
        fi
    }
    echo $port
    return $port
}

#p = $(get_port)
function MAX(){
    a=$1;b=$2;
    if [ $a -gt $b ];then echo $a;
    else echo $b;
    fi
}
function array_filter()
{
    ruleids=()
    i=0;
    for ele;do
    	if [ Chain = $ele ]; then continue; fi
    	if [ num   = $ele ]; then continue; fi
    	ruleids[$i]=$ele
    	i=$(($i+1));
    done

    echo ${ruleids[@]}
    return ${#ruleids[@]}
}

function PrintAll()
{
    if [ ${#ports[*]} -ne ${#users[*]} ];
    then
        _log "users and ports not the same length!!!!!!!!! "
    fi
    echo -ne ${#users[*]}" users\t"${#ports[*]}" ports\n\t"
    len=$(MAX ${#users[@]} ${#ports[@]})
    for(( i=0;i<$len ;i++))
    {        echo -en ${users[$i]}":"${ports[$i]}"\t"
    }
    echo

    echo -ne ${#dbhosts[*]}" dbhosts\t"${#lock_recode[*]}" lock_recode\n"
    for(( i=0;i<${#dbhosts[*]} ;i++))
    {        echo -en "\t"${dbhosts[$i]}
    }
    echo
    for(( i=0;i<${#lock_recode[*]} ;i++))
    {        echo -en "\t\t"${lock_recode[$i]}
    }
    echo
    echo -ne ${#deluser[*]}" deluser\t"${#delport[*]}" delport\n\t"
    len=$(MAX ${#deluser[@]} ${#delport[@]})
    for(( i=0;i<$len ;i++))
    {        echo -en ${deluser[$i]}":"${delport[$i]}"\t"
    }
    echo
}
function finduser()
{
    name=$1
    for (( i = 0 ; i < ${#users[@]} ; i++ ))
    {
        if [ "$name" = "${users[$i]}" ] ;
        then
            echo $i;return 0;
        fi
    }
    _log "finduser error! user$name \nuserlist\t ${users[@]}" 
    echo -1;
    return 1;
}

function adduser()
{
    name=$1
    port=$2
    len=${#users[@]}
    if [ ${#user[@]} -gt ${USER_LIMIT} ];then
        _log "the amount of user counld exceed $USER_LIMIT"
        return 1;
    fi
    if [ -z "${port}" ];then
        _log "user ${name}'s port error $port, add fail"
        return 1;
    fi
    mkdir $name  && cp tornado_test.py $name/ && echo "$port" > $name/port
    touch $name
    if [ $? -eq 0 ];  then
        users[$len]=$name
        ports[$len]=$port
        _log "suceessfully add user:$name($port)"
        return 1;
    else
        _log "add $name($port) meet error (mkdir | cp | echo)"
        return 0;
    fi
}
#head -n 5 /dev/urandom |sed 's/[^a-Z0-9]//g'|strings -n 4
function generate_few_user()
{
    _log " going to add some user"
    if [ ${#users[@]} -gt $USER_LIMIT ]; then return 1; fi;
    ulist=`head -n $((${USER_LIMIT}/2)) /dev/urandom |sed 's/[^a-Z0-9]//g'|strings -n 4`
    for u  in $ulist;do
        port=$(get_port)
        adduser $u $port
    done
    touch .
}

#deleteuser username mode
# mode 0 mean delete the port 
# mode 1 mean delete path of username
function deleteuser()
{
    name=$1; mode=$2
    _log "try delete user ($name)"
    case $mode in 
        0)
        rm $name/port
        ;;
        1)
        rm -r $name
        ;;
        *)
        rm -r $name
        _log "argument wrong"
        ;;
    esac
}
function delete_few_user()
{
    _log "will delete some user "
    deluser=(); delport=();
    if [ ${#users[@]} -eq 0 ];then return 1;fi;
    len=${#users[@]}
    numtodel=$(($RANDOM%$len + 1))
    for(( i=0;i<$numtodel;i++))
    {
        index=$(($RANDOM%$len))
        c=1 #$(($RANDOM%2))
        deleteuser ${users[$index]} $c
        deluser[${#deluser[@]}]=${users[$index]}
        delport[${#delport[@]}]=${ports[$index]}
        ports=(${ports[@]:0:$index} ${ports[@]:$(($index + 1))})
        users=(${users[@]:0:$index} ${users[@]:$(($index + 1))})
        len=$(($len-1))
    }
    touch .
}

function killuser()
{
    name=$1
    pid=`ps -ef | grep $name | grep python |  grep tornado_test.py \
        | grep db | grep uname=$name    | awk -F' ' '{print $2}'`

    if [ ${#pid[@]} -eq 1 ]
    then
        _log "going to kill pid $pid (belong $name)"
        kill -9 $pid
        return 0;
    else
        _log 'kill meet prob but also will try, pid too many or none: '$pid 
        for p in ${pid[@]};do  kill -9 $p; done
        return 1
    fi
}
function kill_few_user()
{
    _log " will kill some users;"
    if [ ${#users[@]} -eq 0 ];then return 1;fi;
    len=${#users[@]}
    numtodel=$(($RANDOM%$len + 1))
    for(( i=0;i<$numtodel;i++))
    {
        index=$(($RANDOM%$len))
        killuser ${users[$index]}
        len=$(($len-1))
        p=${ports[$index]}; ports[$index]=${ports[$len]}; ports[$len]=$p;
        p=${users[$index]}; users[$index]=${users[$len]}; users[$len]=$p;
    }
}


function change_few_user()
{
    _log " change some user "
    if [ ${#users[@]} -eq 0 ];then return 1; fi;
    len=${#users[@]}
    numtodel=$(($RANDOM%$len + 1))
    for(( i=0;i<$numtodel;i++))
    {
        index=$(($RANDOM%$len))
        type=$(($RANDOM%2))
        if [ $type -eq 0 ]; then
            port=$(get_port)
            _log "modi ${users[$index]}的port ${ports[$index]} to $port"
            ports[$index]=$port
            echo $port > ${users[$index]}/port
        else
            name=`head -n 5 /dev/urandom |sed 's/[^a-Z0-9]//g'|strings -n 4 | head -n 1`
            mv ${users[$index]} $name
            if [ $? -eq 0 -a -d $name ];then 
                _log "successfully mod name ${users[$index]} to $name"
                users[$index]=$name
            else _log "change ${users[$index]}'s name to $name meet error"
            fi
        fi
        len=$(($len-1))
        t=${ports[$index]};ports[$index]=${ports[$len]};ports[$len]=$t;
        t=${users[$index]};users[$index]=${users[$len]};users[$len]=$t;
        touch $name
    }

    touch .
}

function unlock_db()
{
    dbhost=$1
    i=$(finddb $dbhost)
    if [ $i -lt 0 ];then _log "meet error when find db"; fi
    while true;do
       ruleid=`iptables -L -n --line-numbers | grep $dbhost | cut -d ' ' -f 1`
       ri=$(array_filter $ruleid); cnt=$?;
       if [ $cnt -gt 0 ];then
           if [ $cnt -gt 1 ];then 
               _log "iptables rules trouble"
           fi
           for r in ${ri[@]};do
               echo "TRY Unlock $dbhost " >&2
               iptables -D INPUT $r;
               break;
           done
       else  break;
       fi
    done
    lock_recode[$i]=1;
}

function block_db()
{
    dbhost=$1
    i=$(finddb $dbhost)
    iptables -A INPUT -s $dbhost -j DROP
    #iptables -L -n --line-numbers 
    lock_recode[$i]=0;
}
function random_play_db()
{
    echo -en " db random play will "
    alive_left=0;
    for(( i=0;i<${#dbhosts[*]};i++))
    { alive_left=$(($alive_left+${lock_recode[$i]}))
    }
    mode=$(($RANDOM%2))
    if [ $alive_left -eq 1 -a $mode -eq 0 ];then  mode=1;  fi
    if [ $alive_left -eq 3 -a $mode -eq 1 ];then  mode=0;  fi
    t=('block' 'unlock'); echo -en ${t[$mode]}

    if [ $mode = 0 ];then
        r=$(($RANDOM%$alive_left))
        echo " $(($r+1)).th alive one "
        for(( i=0;i<${#dbhosts[@]};i++ )){
            if [ ${lock_recode[$i]} = 1 ];then
                if [ $r -eq 0 ];then block_db ${dbhosts[$i]}; break; fi
                r=$(($r-1));
            fi
        }
    else
        r=$(($RANDOM%(${#dbhosts[@]}-$alive_left) ))
        echo " $(($r+1)).th dead one "
        for(( i=0;i<${#dbhosts[@]};i++ )){
            if [ ${lock_recode[$i]} = 0 ];then
                if [ $r -eq 0 ];then unlock_db ${dbhosts[$i]}; break; fi
                r=$(($r-1));
            fi
        }
    fi
    _log "random play done"
}
function shutdown_daemon()
{
    _log "try to shutdown the daemon"
    #verify there is a daemon watch the current path first
    if [ -f ${MONITOR_PID_FILE} ];then
    	MONITOR_PID=`cat ${MONITOR_PID_FILE}`
    	MONITOR_RUNNING=`ps -ef | grep $MONITOR_PID | grep python | grep main.py`
    	if [ -z "$MONITOR_RUNNING" ];
            then _log "there'is no monitor watch this path ,start it your self";
        else 
            kill -9 ${MONITOR_PID_FILE}
            _log "have try to kill daemon"
            rm ${MONITOR_PID_FILE}
        fi
    fi
}

function verify()
{
    LASTROUND_CHECK_RES=0;
    for(( i=0;i<${#users[@]};i++))
    {
        psinfo=`ps -ef | grep uname=${users[$i]} | grep python | grep tornado_test.py | grep port=${ports[$i]}`
        if [ -z "$psinfo" ];then
            LASTROUND_CHECK_RES=-1
            _log "there don't exists ${users[$i]} process in ps ${ports[$i]}"
            echo  `date +%H:%M:%S`"there don't exists ${users[$i]} process in ps ${ports[$i]}" >>error
        else
            wget "http://localhost:${ports[$i]}/runinfo" -T 1 -O temp -q
            if [ $? -ne 0 ] ;then 
                LASTROUND_CHECK_RES=-1
                _log "!!  ERROR when wget res from ${users[$i]}  http://localhost:${ports[$i]}/runinfo/"
                echo `date +%H:%M:%S`"!!  ERROR when wget res from ${users[$i]}:${ports[$i]} " >>error
                continue;
            fi
            pid=`echo $psinfo | awk -F' ' '{print $2}'`
            grep ${ports[$i]} temp -q && grep $pid temp -q
            if [ $? -ne 0 ];then
                LASTROUND_CHECK_RES=-1
                _log  "!! ITS web result is not right ${users[$i]} ${ports[$i]}\n\n"
                _log  `date +%H:%M:%S`"!! ITS web result is not right ${users[$i]} ${ports[$i]}\n\n" >>error
                cat temp >> error
                continue
            fi
        fi
    }

    for(( i=0;i<${#deluser[@]};i++))
    {
        psinfo=`ps -ef | grep uname=${deluser[$i]} | grep python | grep tornado_test.py | grep port=${delport[$i]}`
        if [ "$psinfo" ];then
            LASTROUND_CHECK_RES=-1
            _log "there should't exists ${deluser[$i]}(port${delport[$i]}) process in ps "
            echo `date +%H:%M:%S`"there should't exists ${deluser[$i]}(port${delport[$i]}) process in ps ">>error
        fi
    }
    if (( ${LASTROUND_CHECK_RES} ));then  echo -en '\033[41;37;1m'; fi
    PrintAll
    echo -en '\033[0m'
}


function newverify()
{
    echo 'number of user '${#users[@]}
}
function random_do_test()
{
    if (( $LASTROUND_CHECK_RES != 0 ));then
        sleep ${ROUND_TIME}
        verify
        return 1
    fi
    choice=$(($RANDOM%4));
    if [ ${#users[@]} -eq 0 ]; then choice=0; fi

    case $choice in
        0)  generate_few_user; ;;
        #1)  change_few_user; ;;
        1)  delete_few_user; ;;
        2)  kill_few_user; ;;
        3)  random_play_db; ;;
        4)  shutdown_daemon; ;;
        *)  _log "what a fucking choice you have made";  ;;
    esac
    echo "总数""${#users[@]}"
    sleep ${ROUND_TIME}
    verify
    return 0;
}
function test()
{
    random_play_db
    echo -ne ${#dbhosts[*]}" dbhosts\t"${#lock_recode[*]}" lock_recode\n"
    for(( i=0;i<${#dbhosts[*]} ;i++))
    {        echo -en "\t"${dbhosts[$i]}
    }
    echo
    for(( i=0;i<${#lock_recode[*]} ;i++))
    {        echo -en "\t\t"${lock_recode[$i]}
    }
    echo
    sleep ${ROUND_TIME}
    return 0;
}
function main()
{
    #verify there is a daemon watch the current path first
    #if [ -f "${MONITOR_PID_FILE}" ];then
    #    echo " here find the file"
    #	MONITOR_PID=`cat ${MONITOR_PID_FILE}`
    #	MONITOR_RUNNING=`ps -ef | grep $MONITOR_PID | grep python | grep main.py`
    #	if [ -z "${MONITOR_RUNNING}" ];
    #        then _log "there'is no monitor watch this path ,start it your self";
    #        exit 2; 
    #    fi
    #else
    #    _log "there'is no monitor watch this path ,start it your self"
    #    exit 2;
    #fi
    #delete all user in the current path
    ls -alF | grep "^d" | awk -F' '  '{print $9 }' | grep -v "^\." | xargs rm -r
    sleep 0.5
    #clear all block iptables
    ruleid=`iptables -L -n --line-numbers |  cut -d ' ' -f 1`
    array_filter $ruleid

    time=$?
    for((i=0;i<$time;i++)){
    	iptables -D INPUT 1
    }
    >error
    ROUND_COUNT=1
    while true;
    do
    	_log "+++++++++++++++++++++++ start test round ${ROUND_COUNT} +++++++++++++++++++++++"
    	random_do_test
    	ROUND_COUNT=$(($ROUND_COUNT + 1))
    done
}
main
#for i in `seq 150`;
#do
#	echo "to get the $i" >&2
#	init
#	a=$(get_port)
#	#echo "call_deep = "$call_deep
#	ports[${#ports[@]}]=$a
#done
#len=${#ports[@]}
#for(( i=0;i<$len ;i++))
#{        echo -en ":"${ports[$i]}"\t"
#}
#echo
#


