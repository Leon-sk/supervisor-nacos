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
                    for tmp in nacosconfig.strip().split(','):
                        config, flag = tmp.strip().split(':')
                        filepath, filename = os.path.split(config)
                        os.makedirs(filepath, exist_ok=True)
                        ip, port = info['serverurl'].strip('http://').split(':')
                        data_id = '{0}:{1}:{2}:{3}'.format(info['name'], ip, port, filename)
                        group = info['nacosgroup']
                        app_name = info['name']
                        
                        content = self.nacosclient.get_config(data_id, group)
                        if not content:
                            if os.path.exists(config):
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
    
    def make_callback(self, namespec, action):
        from supervisor.http import NOT_DONE_YET
        from supervisor.options import split_namespec
        from supervisor.xmlrpc import SystemNamespaceRPCInterface
        from supervisor.xmlrpc import RootRPCInterface
        from supervisor.rpcinterface import SupervisorNamespaceRPCInterface
        from supervisor.xmlrpc import Faults
        from supervisor.xmlrpc import RPCError

        # the rpc interface code is already written to deal properly in a
        # deferred world, so just use it
        main = ('supervisor', SupervisorNamespaceRPCInterface(self.supervisord))
        system = ('system', SystemNamespaceRPCInterface([main]))

        rpcinterface = RootRPCInterface([main, system])

        if action:

            if action == 'refresh':

                def donothing():
                    message = 'Page refreshed at %s' % time.ctime()
                    return message

                donothing.delay = 0.05
                return donothing

            elif action == 'stopall':
                callback = rpcinterface.supervisor.stopAllProcesses()

                def stopall():
                    if callback() is NOT_DONE_YET:
                        return NOT_DONE_YET
                    else:
                        return 'All stopped at %s' % time.ctime()

                stopall.delay = 0.05
                return stopall

            elif action == 'restartall':
                callback = rpcinterface.system.multicall(
                    [ {'methodName':'supervisor.stopAllProcesses'},
                      {'methodName':'supervisor.startAllProcesses'} ])

                def restartall():
                    result = callback()
                    if result is NOT_DONE_YET:
                        return NOT_DONE_YET
                    return 'All restarted at %s' % time.ctime()

                restartall.delay = 0.05
                return restartall

            elif namespec:

                def wrong():
                    return 'No such process named %s' % namespec

                wrong.delay = 0.05
                group_name, process_name = split_namespec(namespec)
                group = self.supervisord.process_groups.get(group_name)
                if group is None:
                    return wrong
                process = group.processes.get(process_name)
                if process is None:
                    return wrong

                if action == 'start':
                    try:
                        bool_or_callback = (
                            rpcinterface.supervisor.startProcess(namespec)
                            )
                    except RPCError as e:
                        if e.code == Faults.NO_FILE:
                            msg = 'no such file'
                        elif e.code == Faults.NOT_EXECUTABLE:
                            msg = 'file not executable'
                        elif e.code == Faults.ALREADY_STARTED:
                            msg = 'already started'
                        elif e.code == Faults.SPAWN_ERROR:
                            msg = 'spawn error'
                        elif e.code == Faults.ABNORMAL_TERMINATION:
                            msg = 'abnormal termination'
                        else:
                            msg = 'unexpected rpc fault [%d] %s' % (
                                e.code, e.text)

                        def starterr():
                            return 'ERROR: Process %s: %s' % (namespec, msg)

                        starterr.delay = 0.05
                        return starterr

                    if callable(bool_or_callback):

                        def startprocess():
                            try:
                                result = bool_or_callback()
                            except RPCError as e:
                                if e.code == Faults.SPAWN_ERROR:
                                    msg = 'spawn error'
                                elif e.code == Faults.ABNORMAL_TERMINATION:
                                    msg = 'abnormal termination'
                                else:
                                    msg = 'unexpected rpc fault [%d] %s' % (
                                        e.code, e.text)
                                return 'ERROR: Process %s: %s' % (namespec, msg)

                            if result is NOT_DONE_YET:
                                return NOT_DONE_YET
                            return 'Process %s started' % namespec

                        startprocess.delay = 0.05
                        return startprocess
                    else:

                        def startdone():
                            return 'Process %s started' % namespec

                        startdone.delay = 0.05
                        return startdone

                elif action == 'stop':
                    try:
                        bool_or_callback = (
                            rpcinterface.supervisor.stopProcess(namespec)
                            )
                    except RPCError as e:
                        msg = 'unexpected rpc fault [%d] %s' % (e.code, e.text)

                        def stoperr():
                            return msg

                        stoperr.delay = 0.05
                        return stoperr

                    if callable(bool_or_callback):

                        def stopprocess():
                            try:
                                result = bool_or_callback()
                            except RPCError as e:
                                return 'unexpected rpc fault [%d] %s' % (
                                    e.code, e.text)
                            if result is NOT_DONE_YET:
                                return NOT_DONE_YET
                            return 'Process %s stopped' % namespec

                        stopprocess.delay = 0.05
                        return stopprocess
                    else:

                        def stopdone():
                            return 'Process %s stopped' % namespec

                        stopdone.delay = 0.05
                        return stopdone

                elif action == 'restart':
                    results_or_callback = rpcinterface.system.multicall(
                        [ {'methodName':'supervisor.stopProcess',
                           'params': [namespec]},
                          {'methodName':'supervisor.startProcess',
                           'params': [namespec]},
                          ]
                        )
                    if callable(results_or_callback):
                        callback = results_or_callback

                        def restartprocess():
                            results = callback()
                            if results is NOT_DONE_YET:
                                return NOT_DONE_YET
                            return 'Process %s restarted' % namespec

                        restartprocess.delay = 1
                        return restartprocess
                    else:

                        def restartdone():
                            return 'Process %s restarted' % namespec

                        restartdone.delay = 1
                        return restartdone

                elif action == 'clearlog':
                    try:
                        callback = rpcinterface.supervisor.clearProcessLogs(
                            namespec)
                    except RPCError as e:
                        msg = 'unexpected rpc fault [%d] %s' % (e.code, e.text)

                        def clearerr():
                            return msg

                        clearerr.delay = 0.05
                        return clearerr

                    def clearlog():
                        return 'Log for %s cleared' % namespec

                    clearlog.delay = 0.05
                    return clearlog

        raise ValueError(action)
            
    def restartProcess(self, name):
        try:
            callback = self.make_callback(name, 'restart')
            message = callback()
            logger.info('restart process message:{0}'.format(message))
        except Exception as ex:
            logger.error('error:{0}'.format(ex))
            logger.error(traceback.format_exc())
    
    def getAllProcessInfo(self):
        from supervisor.xmlrpc import RootRPCInterface
        from supervisor.rpcinterface import SupervisorNamespaceRPCInterface
        supervisord = self.supervisord
        rpcinterface = RootRPCInterface(
            [('supervisor',
              SupervisorNamespaceRPCInterface(supervisord))]
        )

        return rpcinterface.supervisor.getAllProcessInfo()
