# coding:utf-8
import json
from multiprocessing import Process

import gevent

import requests
import time
import config
from db.DataStore import sqlhelper
from util.exception import Test_URL_Fail

from gevent import monkey

monkey.patch_all()


def detect_from_db(myip, proxy, proxies_set):
    proxy_dict = {'ip': proxy[0], 'port': proxy[1]}
    result = detect_proxy(myip, proxy_dict)
    if result:
        if proxy[2] < 60000:
            score = proxy[2] + 1
        else:
            score = 60000
        proxy_str = '%s:%s' % (proxy[0], proxy[1])
        proxies_set.add(proxy_str)
        sqlhelper.update({'ip': proxy[0], 'port': proxy[1]}, {'score': score})
    else:
        sqlhelper.delete({'ip': proxy[0], 'port': proxy[1]})

    pass


def validator(queue1, queue2, myip):
    tasklist = []
    while True:
        try:
            # proxy_dict = {'source':'crawl','data':proxy}
            proxy = queue1.get(timeout=10)
            tasklist.append(proxy)
            if len(tasklist) > 500:
                p = Process(target=process_start, args=(tasklist, myip, queue2))
                p.start()
                tasklist = []
        except Exception, e:
            if len(tasklist) > 0:
                p = Process(target=process_start, args=(tasklist, myip, queue2))
                p.start()
                tasklist = []


def process_start(tasks, myip, queue2):
    spawns = []
    for task in tasks:
        spawns.append(gevent.spawn(detect_proxy, myip, task, queue2))
    gevent.joinall(spawns)


def detect_proxy(selfip, proxy, queue2=None):
    '''
    :param proxy: ip字典
    :return:
    '''
    ip = proxy['ip']
    port = proxy['port']
    proxies = {"http": "http://%s:%s" % (ip, port), "https": "http://%s:%s" % (ip, port)}
    protocol, types, speed = checkProxy(selfip, proxies)
    if protocol > 0:
        proxy['protocol'] = protocol
        proxy['type'] = types
        proxy['speed'] = speed
    else:
        proxy = None
    if queue2:
        queue2.put(proxy)
    return proxy


def checkProxy(selfip, proxies):
    '''
    用来检测代理的类型，突然发现，免费网站写的信息不靠谱，还是要自己检测代理的类型
    :param
    :return:
    '''
    protocol = -1
    types = -1
    speed = -1
    http, http_types, http_speed = _checkHttpProxy(selfip, proxies)
    https, https_types, https_speed = _checkHttpProxy(selfip, proxies, False)
    if http and https:
        protocol = 2
        types = http_types
        speed = http_speed
    elif http:
        types = http_types
        protocol = 0
        speed = http_speed
    elif https:
        types = https_types
        protocol = 1
        speed = https_speed
    else:
        types = -1
        protocol = -1
        speed = -1
    return protocol, types, speed


def _checkHttpProxy(selfip, proxies, isHttp=True):
    types = -1
    speed = -1
    if isHttp:
        test_url = config.TEST_HTTP_HEADER
    else:
        test_url = config.TEST_HTTPS_HEADER
    try:
        start = time.time()
        r = requests.get(url=test_url, headers=config.HEADER, timeout=config.TIMEOUT, proxies=proxies)
        if r.ok:
            speed = round(time.time() - start, 2)
            content = json.loads(r.text)
            headers = content[u'headers']
            ip = content[u'origin']
            x_forwarded_for = headers.get(u'X-Forwarded-For', None)
            x_real_ip = headers.get(u'X-Real-Ip', None)
            if selfip in ip:
                return False, types, speed
            elif x_forwarded_for is None and x_real_ip is None:
                types = 0
            elif selfip not in x_forwarded_for and selfip not in x_real_ip:
                types = 1
            else:
                types = 2
            return True, types, speed
        else:
            return False, types, speed

    except Exception, e:
        return False, types, speed


def getMyIP():
    try:
        r = requests.get(url=config.TEST_IP, headers=config.HEADER, timeout=config.TIMEOUT)
        ip = json.loads(r.text)
        return ip['origin']
    except Exception, e:
        raise Test_URL_Fail


if __name__ == '__main__':
    pass
    # ip = '124.88.67.81'
    # port = '80'
    # proxies = {"http": "http://%s:%s" % (ip, port), "https": "http://%s:%s" % (ip, port)}
    # r = requests.get(url=config.TEST_HTTP_HEADER, headers=config.HEADER, timeout=config.TIMEOUT,proxies=proxies)
    # json = json.loads(r.text)
    # print json['headers']
    # print json['origin']
    # getMyIP()


    # j = json.dumps(str)
    # str = j['ip']
    # print str