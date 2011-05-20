#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import codecs
import urllib
from xml.dom.minidom import parse, parseString

from client import DoubanOAuth
from model import Entry, Account, get_str

DEBUG = True

ME_URI = "/people/@me"
MINIBLOG_URI = "/people/@me/miniblog"


class DoubanRobot(object):
    account = None
    def __init__(self, key=None, secret=None):
        self.client = DoubanOAuth()
        if key and secret:
            self.client.login(key, secret)
    
    def get(self, url, param=None):
        return self.client.request('GET', url, param=param)
    
    def get_miniblogs(self):
        if self.account is None:
            self.get_current_user()
        url = MINIBLOG_URI
        xml = self.get(url, param={"max-results":"10"}).read()
        
        dom = parseString(xml)
        entries = dom.getElementsByTagName('entry')
        entry_list = []
        for entry in entries:
            entry_list.append(Entry(entry))
            #print entry_list[-1].to_send
        #entry_list.sort(cmp=lambda x,y: cmp(x.time, y.time))
        return entry_list
    
    def get_auth_url(self):
        return self.client.auth_url()
    
    def get_access_token(self, token_key, token_secret):
        self.client.get_access_token(token_key, token_secret)
        
    def get_current_user(self):
        xml = self.get(ME_URI).read()
        
        dom = parseString(xml)
        account = Account(dom)
        user = { "name":account.title, "uid":account.uid }
        return user
        
    @property
    def token_key(self):
        return self.client.token_key
    
    @property
    def token_secret(self):
        return self.client.token_secret


def escape(s):
    return urllib.quote(s, safe='~')
        

def test():
    robot = DoubanRobot()
    robot.get_miniblogs()
    #robot.fetch_mails()
        
    
if __name__ == '__main__':
    test()