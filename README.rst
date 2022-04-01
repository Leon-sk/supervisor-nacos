Supervisor
==========

Supervisor is a client/server system that allows its users to
control a number of processes on UNIX-like operating systems.

配置示例
-------------------
[unix_http_server]
file=/tmp/supervisor.sock   ; the path to the socket file

[inet_http_server]         ; inet (TCP) server disabled by default
port=127.0.0.1:9001        ; ip_address:port specifier, *:port for all iface
username=user              ; default is no username (open server)
password=123               ; default is no password (open server)

[nacos]
server_addresses=192.168.1.108:8848, ;nacos server_addresses
username=nacos              ; nacos username
password=nacos              ; nacos password
namespace=3ee2e3c5-43ca-433b-921f-65017248b750 ;nacos namespaceh

[supervisord]
logfile=/tmp/supervisord.log ; main log file; default $CWD/supervisord.log
logfile_maxbytes=50MB        ; max main logfile bytes b4 rotation; default 50MB
logfile_backups=10           ; # of main logfile backups; 0 means none, default 10
loglevel=info                ; log level; default info; others: debug,warn,trace
pidfile=/tmp/supervisord.pid ; supervisord pidfile; default supervisord.pid
nodaemon=true               ; start in foreground if true; default false
silent=false                 ; no logs to stdout if true; default false
minfds=1024                  ; min. avail startup file descriptors; default 1024
minprocs=200                 ; min. avail process descriptors;default 200

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket

[program:snmp_exporter]
serverurl = http://127.0.0.1:9117 ;http://ip:port
nacosgroup = 210000
nacosconfig = /home/zc/data/source_code/snmp_exporter/snmp.yml:True ;path/config:restart
autorestart = True
autostart = True
command     = /home/zc/data/source_code/snmp_exporter/snmp_exporter --web.listen-address=:9117 --config.file=/home/zc/data/source_code/snmp_exporter/snmp.yml
directory   = /home/zc/data/source_code/snmp_exporter/
user        = root
startsecs   = 10
startretries = 10
stopasgroup = true
killasgroup = true
redirect_stderr         = true
stdout_logfile_maxbytes = 50MB
stdout_logfile_backups  = 3
stdout_logfile          = /home/zc/data/source_code/snmp_exporter/log/snmp_exporter.log
