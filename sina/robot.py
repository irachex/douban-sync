#!/usr/bin/env python
# -*- coding: UTF-8 -*-


'''
Created on Aug 2, 2010

@author: ting
'''

from weibopy.auth import OAuthHandler
from weibopy.api import API

from config import WEIBO_API_KEY as API_KEY, WEIBO_API_SECRET as API_SECRET

class WeiboRobot(object):
    auth = None
    
    def __init__(self, key=None, secret=None):
        self.api_key= API_KEY
        self.api_secret = API_SECRET
        if key and secret:
            self.login(key, secret)
        
    def getAtt(self, key):
        try:
            return self.obj.__getattribute__(key)
        except Exception, e:
            print e
            return ''
        
    def getAttValue(self, obj, key):
        try:
            return obj.__getattribute__(key)
        except Exception, e:
            print e
            return ''
        
    def login(self, key=None, secret=None):  
        if key and secret:
            self.auth = OAuthHandler(self.api_key, self.api_secret)
            self.auth.setToken(key, secret)
            self.api = API(self.auth)
            return
        self.auth = OAuthHandler(self.api_key, self.api_secret)
        auth_url = self.auth.get_authorization_url()
        print 'Please authorize: ' + auth_url
        verifier = raw_input('PIN: ').strip()
        self.auth.get_access_token(verifier)
        self.api = API(self.auth)
  
    def send(self, message):
        message = message.encode("utf-8")
        status = self.api.update_status(message)
        #self.obj = status
        #id = self.getAtt("id")
        #text = self.getAtt("text")
        #print "update---"+ str(id) +":"+ text
        
    def destroy_status(self, id):
        status = self.api.destroy_status(id)
        self.obj = status
        #id = self.getAtt("id")
        #text = self.getAtt("text")
        #print "update---"+ str(id) +":"+ text

if __name__ == '__main__':
    test = SinaRobot()
    test.login()
    test.send("test sync from douban")

