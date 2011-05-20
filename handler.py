#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import random
import urllib
import datetime
import time
import base64
import hmac
import hashlib

from google.appengine.api import taskqueue
from google.appengine.api import mail as gmail
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from douban.robot import DoubanRobot
from weibopy.auth import OAuthHandler
from weibopy.error import WeibopError
from sina.robot import WeiboRobot
from model import User, Entry
from fetch import fetch
from config import WEIBO_API_KEY, WEIBO_API_SECRET, COOKIE_SECRET


class BaseHandler(webapp.RequestHandler):
    user = None
    def get_current_user(self):
        if self.user is None:
            uid = self.get_cookie("uid")
            if uid is None:
                return None
            self.user = {}
            self.user["uid"] = uid
            self.user["name"] = self.get_cookie("name")
            self.user["weibo_name"] = self.get_cookie("weibo_name")
            if self.user["weibo_name"] is None:
                user = User.get_by_key_name(self.user["uid"])
                if user is not None and user.weibo_key and user.weibo_secret:
                    try:
                        weibot = WeiboRobot(user.weibo_key, user.weibo_secret)
                        self.user["weibo_name"] = weibot.auth.get_username()
                        self.set_cookie("weibo_name", self.user["weibo_name"])
                    except WeibopError,e:
                        pass
        return self.user
            
    def render(self, template_name, data=None):
        temp_path = os.path.join(os.path.dirname(__file__), 'template/%s' % (template_name,))
        self.response.out.write(template.render(temp_path, data))
        
    def set_cookie(self, name, value):
        name = _utf8(name)
        value = _utf8(value)
        value = self.create_sign_value(name, value)
        self.response.headers.add_header('Set-Cookie','%s=%s; expires=%s; path=/;' % (name, value, datetime.datetime.now() + datetime.timedelta(days=30)))
    
    def get_cookie(self, name, default=None):
        if name in self.request.cookies:
            value = self.request.cookies[name]
        else :
            value = default
        if not value:
            return None
        parts = value.split("|")
        if len(parts) != 3: 
            return None
        signature = self._cookie_signature(name, parts[0], parts[1])
        if not _time_independent_equals(parts[2], signature):
            logging.warning("Invalid cookie signature %r", value)
            return None
        timestamp = int(parts[1])
        if timestamp < time.time() - 31 * 86400:
            logging.warning("Expired cookie %r", value)
            return None
        if timestamp > time.time() + 31 * 86400:
            logging.warning("Cookie timestamp in future; possible tampering %r", value)
            return None
        if parts[1].startswith("0"):
            logging.warning("Tampered cookie %r", value)
        try:
            return base64.b64decode(parts[0])
        except:
            return None
    
    def clear_cookie(self):
        expires = datetime.datetime.now() - datetime.timedelta(weeks=2)
        self.response.headers.add_header("Set-Cookie", "uid=0;expires=%s; path=/" % expires)
        self.response.headers.add_header("Set-Cookie", "name=0;expires=%s; path=/" % expires)
        self.response.headers.add_header("Set-Cookie", "weibo_name=0;expires=%s; path=/" % expires)
        
    
    def create_sign_value(self, name, value):
        timestamp = str(int(time.time()))
        value = base64.b64encode(value)
        signature = self._cookie_signature(name, value, timestamp)
        value = "|".join([value, timestamp, signature])
        return value

    def _cookie_signature(self, *parts):
        hash = hmac.new(COOKIE_SECRET, digestmod=hashlib.sha1)
        for part in parts: 
            hash.update(part)
        return hash.hexdigest()        


class HomeHandler(BaseHandler):
    def get(self):
        if self.get_current_user() is None:
            self.redirect("/auth/")
        elif self.user["weibo_name"] is None:
            self.redirect("/auth/weibo/")
        else:
            self.render("home.html", { "uid" : self.user["uid"],
                                       "name" : self.user["name"] , 
                                       "weibo_name":self.user["weibo_name"] })
            

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie()
        self.redirect("/")

         
class StopHandler(BaseHandler):
    def get(self, uid):
        if (self.get_current_user() is None) or (self.user["uid"] != uid):
            self.redirect("/auth/")
        user = User.get_by_key_name(uid)
        user.delete()            
        self.render("msg.html", { "msg" : "取消成功", "url" : "/auth/" })
               

class DoubanAuthHandler(BaseHandler):
    def get(self):
        if self.get_current_user() is not None:
            user = User.get_by_key_name(self.user["uid"])
            if user is not None:
                try:
                    dobot = DoubanRobot(user.douban_key, user.douban_secret)
                    dobot.get_current_user()
                    self.redirect("/auth/weibo/")
                except Exception,e:
                    pass
            
        doubanbot = DoubanRobot()

        callback = self.request.get("callback").strip()
        if callback == "true":
            token_key = self.request.get("oauth_token").strip()
            token_secret = self.request.get("oauth_secret").strip()
            doubanbot.get_access_token(token_key, token_secret)
            
            account = doubanbot.get_current_user()
            user = User.get_or_insert(account["uid"])
            user.name = account["name"]
            user.douban_key=doubanbot.token_key
            user.douban_secret=doubanbot.token_secret
            user.put()
            
            self.set_cookie("uid", account["uid"])
            self.set_cookie("name", account["name"])
            
            self.redirect("/auth/weibo/")
    
        temp_data = { "douban_url":doubanbot.get_auth_url() + "&oauth_callback=" + escape(self.request.url+"?callback=true&oauth_secret=" + doubanbot.token_secret)}
        self.render("douban_auth.html", temp_data)
    
    
class WeiboAuthHandler(BaseHandler):
    def get(self):
        if self.get_current_user() is None:
            self.redirect("/auth/")
        else:
            user = User.get_by_key_name(self.user["uid"])
            if user is not None and user.weibo_key and user.weibo_secret:
                try:
                    weibot = WeiboRobot(user.weibo_key, user.weibo_secret)
                    weibot.auth.get_username()
                    self.redirect("/")
                except Exception,e:
                    #logging.info(e.reason)
                    pass
            
        auth = OAuthHandler(WEIBO_API_KEY, WEIBO_API_SECRET)
    
        temp_data = { 
            "name" : self.user["name"],
            "weibo_url" : auth.get_authorization_url(),
            "token":auth.request_token.key, 
            "secret":auth.request_token.secret 
        }
        self.render("weibo_auth.html", temp_data)
    
    def post(self):
        if self.get_current_user() is None:
            self.redirect("/auth/")
        
        auth = OAuthHandler(WEIBO_API_KEY, WEIBO_API_SECRET)
        
        request_token = self.request.get("request_token")
        request_secret = self.request.get("request_secret")
        auth.set_request_token(request_token, request_secret)
        
        verifier = self.request.get("oauth_verifier").strip()
        try:
            accessToken = auth.get_access_token(verifier)
            weibo_name = auth.get_username()
            self.set_cookie("weibo_name", weibo_name)
            self.user["weibo_name"] = weibo_name
        except Exception,e:
            self.render("msg.html", { "msg" : "授权码错误", "url" : "/auth/weibo/" })
            return
        
        user = User.get_by_key_name(self.user["uid"])
        if not user:
            self.redirect("/auth/")
        user.weibo_key = accessToken.key
        user.weibo_secret = accessToken.secret
        user.sync_time = datetime.datetime.now()
        user.last_id = ""
        user.put()
        
        fqueue = taskqueue.Queue(name='fetch')
        ftask = taskqueue.Task(url='/task/fetch/', params=dict(uid=user.key().name()))
        fqueue.add(ftask)
        
        self.redirect("/")
        

class CronFetchHandler(BaseHandler):
    def get(self):
        nowtime = datetime.datetime.now()
        users = User.all().filter("sync_time <=", nowtime)
        for user in users:
            fqueue = taskqueue.Queue(name='fetch')
            ftask = taskqueue.Task(url='/task/fetch/', params=dict(uid=user.key().name()))
            fqueue.add(ftask)
        

class TaskFetchHandler(BaseHandler):
    def post(self):
        uid= self.request.get("uid")
        fetch(uid)
        
   
def escape(s):
    return urllib.quote(s, safe='~')

def _utf8(s):
    if isinstance(s, unicode):
        return s.encode("utf-8")
    assert isinstance(s, str)
    return s
        
def _time_independent_equals(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0
    
    
application = webapp.WSGIApplication([
                   (r'/', HomeHandler),
                   (r'/logout/', LogoutHandler),
                   (r'/stop/(.*)/', StopHandler),
                   (r'/auth/', DoubanAuthHandler),
                   (r'/auth/douban/', DoubanAuthHandler),
                   (r'/auth/weibo/', WeiboAuthHandler),
                   (r'/cron/fetch/', CronFetchHandler),
                   (r'/task/fetch/', TaskFetchHandler),
              ], debug=True)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()