#!/usr/local/bin/env python3
# -*-  coding:utf-8 -*-

import time
import threading
import logging
import traceback
import os

from supervisor.states import ProcessStates
from supervisor.nacos import NacosClient

logger = logging.getLogger('nacos')


class Nacos:

    def __init__(self, supervisord):
        self.supervisord = supervisord
        self.registering = False
        self.listening = False
        self.nacosclient = None
        self.nacos_config = self.supervisord.options.nacos_config
        self.watcher_config = {}

    def start(self):
        self.nacosclient = NacosClient(self.nacos_config['server_addresses'], namespace=self.nacos_config['namespace'],
                                       username=self.nacos_config['username'], password=self.nacos_config['password'])
        self.__startRegisterInstance()
        self.__startListenConfigs()

    def stop(self):
        self.registering = False
        self.listening = False

    def __startRegisterInstance(self):
        if not self.registering:
            self.registering = True
            threading.Thread(target=self.__registerInstanceLoop,
                             args=(), kwargs={},).start()

    def __registerInstanceLoop(self):
        while self.registering:
            try:
                allProcessInfo = self.getAllProcessInfo()
                if not allProcessInfo:
                    time.sleep(5)
                    continue
                for info in allProcessInfo:
                    state = info['state']
                    ip, port = info['serverurl'].strip('http://').split(':')
                    metadata = self.nacos_config['metadata']
                    if state == ProcessStates.RUNNING:
                        self.nacosclient.add_naming_instance(
                            info['name'], ip, port, group_name=info['nacosgroup'], metadata=metadata)
                        self.nacosclient.send_heartbeat(
                            info['name'], ip, port, group_name=info['nacosgroup'], metadata=metadata)
                    else:
                        self.nacosclient.remove_naming_instance(
                            info['name'], ip, port, group_name=info['nacosgroup'])
            except Exception as ex:
                logger.error('error:{0}'.format(ex))
                logger.error(traceback.format_exc())
    
    def __startListenConfigs(self):
        if not self.listening:
            self.listening = True
            threading.Thread(target=self.__listenConfigsLoop,
                             args=(), kwargs={},).start()

    def __listenConfigsLoop(self):
        while self.listening:
            try:
                allProcessInfo = self.getAllProcessInfo()
                if not allProcessInfo:
                    time.sleep(5)
                    continue
                for info in allProcessInfo:
                    nacosconfig = info['nacosconfig']
                    config, flag = nacosconfig.strip().split(':')
                    filepath, filename = os.path.split(config)
                    os.makedirs(filepath, exist_ok=True)
                    ip, port = info['serverurl'].strip('http://').split(':')
                    data_id = '{0}:{1}:{2}:{3}'.format(info['name'], ip, port, filename)
                    group = info['nacosgroup']
                    app_name = info['name']
                    
                    content = self.nacosclient.get_config(data_id, group)
                    if not content:
                        with open(config, 'r') as f:
                            content = f.read()
                        self.nacosclient.publish_config(data_id, group, content, app_name=app_name)
                    else:
                        self.nacosclient.add_config_watcher(data_id, group, self.watcher_callback)
                    
                    self.save_watcher_config(data_id, group, config, flag, info['name'])
                    
            except Exception as ex:
                logger.error('error:{0}'.format(ex))
                logger.error(traceback.format_exc())
    
    def save_watcher_config(self, data_id, group, config, flag, name):
        cache_key = '{0}:{1}:{2}'.format(data_id, group, self.nacosclient.namespace)
        self.watcher_config[cache_key] = {
            'config':config,
            'flag':flag,
            'name':name
            }
    
    def get_watcher_config(self, data_id, group):
        cache_key = '{0}:{1}:{2}'.format(data_id, group, self.nacosclient.namespace)
        return self.watcher_config.get(cache_key)

    def watcher_callback(self, params):
        data_id = params.get('data_id')
        group = params.get('group')
        content = params.get('content')
        
        config = self.get_watcher_config(data_id, group)
        if config and content:
            with open(config.get('config'), 'w') as f:
                f.write(content)
            if eval(config.get('flag')) :
                self.restartProcess(config.get('name'))
            
    def restartProcess(self, name):
        from supervisor.xmlrpc import RootRPCInterface
        from supervisor.rpcinterface import SupervisorNamespaceRPCInterface
        supervisord = self.supervisord
        rpcinterface = RootRPCInterface(
            [('supervisor',
              SupervisorNamespaceRPCInterface(supervisord))]
        )

        rpcinterface.supervisor.stopProcess(name)
        time.sleep(1)
        rpcinterface.supervisor.startProcess(name)
    
    def getAllProcessInfo(self):
        from supervisor.xmlrpc import RootRPCInterface
        from supervisor.rpcinterface import SupervisorNamespaceRPCInterface
        supervisord = self.supervisord
        rpcinterface = RootRPCInterface(
            [('supervisor',
              SupervisorNamespaceRPCInterface(supervisord))]
        )

        return rpcinterface.supervisor.getAllProcessInfo()
