#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import random
import codecs

from google.appengine.ext import db

class User(db.Model):
    name = db.StringProperty()
    douban_key = db.StringProperty()
    douban_secret = db.StringProperty()
    sync_time = db.DateTimeProperty()
    last_id = db.StringProperty()
    
    weibo_key = db.StringProperty()
    weibo_secret = db.StringProperty()


class Entry(object):
    entry = None
    id = None
    category = None
    content = None
    time = None
    comment = None
    status = None
    rating = None
    to_send = None

    def __init__(self, entry):
        self.entry = entry
        self.id = self.get_by_tag('id')
        self.category = self.get_by_attr('category', 'term')
        self.category = self.category.split('.')[-1]
        self.time = self.get_by_tag('published')
        self.content = self.get_by_tag('content')
        self.comment = self.get_by_name('comment')
        self.status = self.get_by_name('status')
        self.rating = self.get_by_name('rating')

        self.to_send = self.get_send_content()

    def get_by_name(self, name):
        elements = self.entry.getElementsByTagName('db:attribute')
        if elements:
            for e in elements:
                if e.getAttribute('name') == name:
                    return get_str(e)
        return None

    def get_by_tag(self, tag):
        element = self.entry.getElementsByTagName(tag)
        if element:
            return get_str(element[0])
        return None

    def get_by_attr(self, tag, attr):
        element = self.entry.getElementsByTagName(tag)
        if element:
             return element[0].getAttribute(attr)
        return None

    def get_send_content(self):
        content = self.content
        content = content.replace('<a href="', ' ')
        content = content.replace('">', ' ')
        content = content.replace('</a>', ' ')
        if self.comment:
            content += u'「' + self.comment + u'」'
        if self.rating:
            content += u"★"*int(self.rating) + u"☆"*(5-int(self.rating))
        return content


class Account(object):
    title = None
    uid = None
    icon = None
    entry = None

    def __init__(self, entry):
        self.entry = entry
        self.title = self.get_by_tag("title")
        self.uid = self.get_by_tag("db:uid")

    def get_by_tag(self, tag):
        element = self.entry.getElementsByTagName(tag)
        if element:
            return get_str(element[0])
        return None


def get_str(node):
    nodelist = node.childNodes
    rc = []
    for n in nodelist:
        if (n.nodeType == n.TEXT_NODE) or (n.nodeType == n.CDATA_SECTION_NODE):
            rc.append(n.data)
    return ''.join(rc)

def repeat_str(st, cnt=1):
    s = st
    for i in xrange(cnt-1):
        s += st
    return s


