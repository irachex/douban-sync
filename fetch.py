#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import random
import datetime
import time

from douban.robot import DoubanRobot
from weibopy.error import WeibopError
from sina.robot import WeiboRobot
from model import User, Entry
from config import TIME_DELTA


def fetch(uid):
    user = User.get_by_key_name(uid)
    if not user:
        return
    doubanbot = DoubanRobot(user.douban_key, user.douban_secret)
    weibobot = WeiboRobot(user.weibo_key, user.weibo_secret)
    
    entries = doubanbot.get_miniblogs()
    #entries.sort(cmp=lambda x,y: cmp(x.time, y.time))
        
    if not entries:
        user.sync_time = datetime.datetime.now() + datetime.timedelta(seconds=TIME_DELTA)
        user.put()
        return
    cnt = 0
    for entry in reversed(entries):
        if (not user.last_id) or (entry.id > user.last_id):
            try:
                cnt += 1
                weibobot.send(entry.to_send)
            except WeibopError, e:
                # handle error: user has revoked access privilege to this application
                if e.reason.find("40072") != -1:
                    logging.info("Delete binding, because user has revoked access privilege for this application from Sina: " + e.reason);
                    user.delete()
                    return
                # 40028 indicates that the tweet is duplicated or user is in black list
                if e.reason.find("40028") != -1 or e.reason.find("40308") != -1:
                    if e.reason.find("有关部门") != -1:
                        #您输入的网址被有关部门列为恶意网址，无法发表，请谅解。
                        logging.info(entry.to_send)
                        continue
                    logging.info("User is in black list? Skip this tweet and temporary disable sync for 1 hour. " + e.reason)
                    user.sync_time = datetime.datetime.now() + datetime.timedelta(seconds=3600)
                    if cnt>0:
                        user.last_id = entries[-(cnt-1)].id
                    user.put()
                    return
                # ignore "repeated weibo text" error
                if e.reason.find("40025") != -1:
                    logging.info("Error ignored: " + e.reason)
                else:
                    # other error
                    pass
        
    user.last_id = entries[0].id
    user.sync_time = datetime.datetime.now() + datetime.timedelta(seconds=TIME_DELTA)
    user.put()
