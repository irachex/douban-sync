
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re


def parse_datetime(str):

    # We must parse datetime this way to work in python 2.4
    return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0800 %Y')[0:6]))


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):

    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json

