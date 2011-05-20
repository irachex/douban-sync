#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import binascii
import cgi
import hashlib
import hmac
import httplib
import random
import time
import urllib
from config import DOUBAN_API_KEY as API_KEY, DOUBAN_API_SECRET as API_SECRET

SERVER = 'api.douban.com'
 
OAUTH_SERVER = 'www.douban.com'
REQUEST_TOKEN_URI = '/service/auth/request_token'
AUTHORIZATION_URI = '/service/auth/authorize'
ACCESS_TOKEN_URI = '/service/auth/access_token'

SIG_METHOD = 'HMAC-SHA1'
OAUTH_VER = '1.0'
SCHEME = 'http'


def escape(s, safe="~"):
    return urllib.quote(s, safe)
 
def generate_timestamp():
    return str(int(time.time()))
 
def generate_nonce(length=8):
    return ''.join([str(random.randint(0, 9)) for i in range(length)])
 
def normalize_params(params):
    key_values = [(escape(k), escape(v)) for k,v in params.items()]
    key_values.sort()
    return '&'.join(['%s=%s' % (k, v) for k, v in key_values])
 
def sign(method, url, params, secret, token_secret):
    sig = (
              escape(method.upper()),
              escape(SCHEME + '://' +  escape(url, safe="/=")),
              escape(normalize_params(params))
          )
    key = escape(secret) + '&'
    if url == OAUTH_SERVER + ACCESS_TOKEN_URI:
        #I have no idea why the fuck douban uses concatenated secrets as signature instead of the computed one
        return secret + '&' + token_secret
    if token_secret:
        key += escape(token_secret)
    base_string = '&'.join(sig)
    return binascii.b2a_base64(hmac.new(key, base_string, hashlib.sha1).digest())[:-1]
 
def generate_header(method, url, params, key, token):
    header = 'OAuth realm=""'
    params['oauth_version'] = OAUTH_VER
    signature = sign(method, url, params, key, token)
    params['oauth_signature'] = signature
    key_values = [(k, v) for k,v in params.items()]
    key_values.sort()
    for k, v in key_values:
            header += ', %s="%s"' % (k, escape(v,safe="/%?"))
    return {"Authorization": header}
 
def create_connection(server):
    return httplib.HTTPConnection(server)
 
 
class DoubanOAuth(object):
    def __init__(self, key=API_KEY, secret=API_SECRET):
        self.key = API_KEY
        self.secret = API_SECRET
    
    def login(self, token_key=None, token_secret=None):
        if token_key and token_secret:
            self.token_key = token_key
            self.token_secret = token_secret
            return True
        self.get_request_token()
    
    def get_request_token(self):
        conn = create_connection(OAUTH_SERVER)
        params = {
            'oauth_consumer_key': self.key,
            'oauth_signature_method': SIG_METHOD,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce()
        }
        header = generate_header('GET', OAUTH_SERVER + REQUEST_TOKEN_URI, params, self.secret, None)
        
        conn.request("GET", REQUEST_TOKEN_URI, headers=header)
        response = conn.getresponse()
        if response.status == 200:
            data = response.read()
            data = cgi.parse_qs(data, keep_blank_values=False)
            self.token_key = data['oauth_token'][0]
            self.token_secret = data['oauth_token_secret'][0]
        else:
            logging.info( "%s %s\n%s" % (response.status, response.reason, response.read()))
        conn.close()
 
    def authorize_token(self):
        print "Open the link below to authorize the request token:"
        print "http://%s%s?oauth_token=%s" % (OAUTH_SERVER, AUTHORIZATION_URI, escape(self.token_key))
        raw_input("Press enter to continue")
        self.get_access_token()
        
    def get_access_token(self, token_key, token_secret):
        self.token_key = token_key
        self.token_secret = token_secret
        
        conn = create_connection(OAUTH_SERVER)
        params = {
            'oauth_consumer_key': self.key,
            'oauth_token': self.token_key,
            'oauth_sgnature_method': SIG_METHOD,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce()
        }
        header = generate_header("GET", OAUTH_SERVER + ACCESS_TOKEN_URI, params, self.secret, self.token_secret)
        conn.request("GET", ACCESS_TOKEN_URI, headers=header)
        response = conn.getresponse()
        if response.status == 200:
            data = response.read()
            data = cgi.parse_qs(data, keep_blank_values=False)
            self.token_key = data['oauth_token'][0]
            self.token_secret = data['oauth_token_secret'][0]
        else:
            logging.info( "%s %s\n%s" % (response.status, response.reason, response.read()))
        conn.close()
 
    def auth_url(self):
        self.get_request_token()
        url = "http://%s%s?oauth_token=%s" % (OAUTH_SERVER, AUTHORIZATION_URI, escape(self.token_key))
        return url
        
    def request(self, method, url, content=None, param=None):
        if self.token_key is None:
            print 'need auth'
            return None
        conn = create_connection(SERVER)
        params = {
            'oauth_consumer_key': self.key,
            'oauth_token': self.token_key,
            'oauth_signature_method': SIG_METHOD,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce()
        }
        
        if param:
            params.update(param)
            
        header = generate_header(method, SERVER + url, params, self.secret, self.token_secret)
        if method in ('POST', 'PUT'):
            header['Content-Type'] = 'application/atom+xml; charset=utf-8'
        conn.request(method, escape(url,safe="/?=&") , content, header)
        response = conn.getresponse()
        return response
        

if __name__ == '__main__':
    test = DoubanOAuth()
    test.login()
    print test.token_key, test.token_secret
    entry = u'<?xml version=\'1.0\' encoding=\'UTF-8\'?>'\
                            + u'<entry xmlns:ns0="http://www.w3.org/2005/Atom" xmlns:db="http://www.douban.com/xmlns/">'\
                            + u'<content>' +  u'hello from api' + u'</content>'\
                            + u'</entry>'
    #data = test.request('POST', '/miniblog/saying', entry)
    #print data.status, data.reason