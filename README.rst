supervisor-nacos
==============================

1.结合supervis和nacos技术，可自动注册服务、注销服务、保持心跳实现服务的管理，
可通过配置项实现配置自动监控刷新，并根据配置自动重启服务。
2.实现服务自动化监控和控制。

Nacos基本配置
==============================
  [nacos]  
  
  server_addresses=192.168.1.108:8848, ;nacos server_addresses  
  
  username=nacos              ; nacos username  
  
  password=nacos              ; nacos password  

  namespace=3ee2e3c5-43ca-433b-921f-65017248b750 ;nacos namespaceh  
  
自动服务管理、配置刷新
==============================
  [program:snmp_exporter]  
  
  serverurl = http://127.0.0.1:9117 ;http://ip:port  
  
  nacosgroup = 210000  
  
  nacosconfig = /home/zc/data/source_code/snmp_exporter/snmp.yml:True ;path/config:restart  
  
  autorestart = True  
  
  autostart = True  
  
  command     = /opt/snmp_exporter/snmp_exporter --web.listen-address=:9117 --config.file=/opt/snmp_exporter/snmp.yml  
  
  directory   = /opt/snmp_exporter  
  
  user        = root  
  
  startsecs   = 10  
  
  startretries = 10  
  
  stopasgroup = true  
  
  killasgroup = true  
  
  redirect_stderr         = true  
  
  stdout_logfile_maxbytes = 50MB  
  
  stdout_logfile_backups  = 3  
  
  stdout_logfile          = /opt/snmp_exporter/log/snmp_exporter.log  
  
