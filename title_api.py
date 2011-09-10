#!/usr/bin/env python
import tornado.auth
import tornado.escape
import tornado.database
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata
import os.path
import sys
import json
import daemon
# PageGetter
import re
import chardet
from formatter import NullFormatter
import urllib2
import urlparse
from lxml.html import fromstring
# server config
from tornado.options import define, options
define("port", default=3333, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/page/title", MainHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MyDict(dict):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

class PageGetter():
    def get_info(self, url):
        ua = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.55 Safari/533.4'
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', ua)]

        page = opener.open(url)
        charset = page.headers.getparam('charset')
        
        html = unicode(page.read(), charset if charset else 'utf-8') 
        title = self.get_title(html)
        comment = self.get_comment(html)[:300]

        return MyDict({ "status" : "success" , "title" : title, "comment" : comment })

    def get_comment(self, html):
        et = fromstring(html)
        # get description
        metas = et.xpath('./head/meta')
        for meta in metas:
            #print meta.attrib
            if 'name' in meta.attrib and meta.attrib['name'] == 'description' and 'content' in meta.attrib:
                return meta.attrib['content']
        # get text
        xpath = r'//text()[name(..)!="script"][name(..)!="style"]'
        text = ''.join([text for text in et.xpath(xpath) if text.strip()])
        return text

    def get_title(self, html):
        et = fromstring(html)
        title = ex.xpath("./head/title") if et.xpath("./head/title") else 'notitle'
        return title

    def error(self):
        return MyDict({ "status" :  "error" })

class MainHandler(tornado.web.RequestHandler, PageGetter):
    def get(self):
        if self.request.remote_ip != '127.0.0.1':
            self.write(json.dumps({ "status" : "error", "msg" : "invalid access" }))
            return
        url = self.get_argument('url', None)
        url_exp = re.compile(r'^http(s)?://')
        if not url:
            self.write(json.dumps({ "status" : "error", "msg" : "url parameter is required" }))
            return             
        if not url_exp.match(url):
            self.write(json.dumps({ "status" : "error", "msg" : "bad url expression" }))
            return
        else:
            result = self.get_info(url)
            if result.status == "error":
                self.write(json.dumps({ "status" : "error", "msg" : "API failed to get a title from this URL", "page" : {} }))
            else:
                self.write(json.dumps({ "status" : "success", "msg" : "", "page" : { "url" : url, "title" : result.title, "comment" : result.comment } }, ensure_ascii=False))

def main():
    # daemon
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

