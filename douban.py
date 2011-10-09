#!/usr/bin/env python

import re
import logging
import urllib

from tornado.escape import xhtml_escape
from tornado.httputil import url_concat
from tornado.auth import httpclient, OAuthMixin

class DoubanMixin(OAuthMixin):
    """Douban OAuth authentication.

    Register your apps at http://www.douban.com/service/apikey/apply
    Then copy your CONSUMER KEY and CONSUMER SECRET to the application
    setings 'douban_consumer_key' and 'douban_consumer_secret'.

    Example usage::

        class DoubanHandler(tornado.web.RequestHandler, DoubanMixin):
            @tornado.web.asynchronous
            def get(self):
                if self.get_argument("oauth_token", None):
                    self.get_authenticated_user(self.async_callback(self._on_auth))
                    return
                self.authorize_redirect()
            
            def _on_auth(self, user):
                if not user:
                    raise tornado.web.HTTPError(500, "Douban auth failed")
                # do something else
                self.finish()

    """
    _OAUTH_VERSION = "1.0"
    _OAUTH_REQUEST_TOKEN_URL = "http://www.douban.com/service/auth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "http://www.douban.com/service/auth/access_token"
    _OAUTH_AUTHORIZE_URL = "http://www.douban.com/service/auth/authorize"
    _OAUTH_NO_CALLBACKS = False

    def douban_request(self, path, callback, access_token=None,
            post_args=None, **args):
        url = "http://api.douban.com" + path
        if access_token:
            all_args = {}
            all_args.update(args)
            #all_args.update(post_args or {})
            consumer_token = self._oauth_consumer_token()
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                    url, access_token, all_args, method=method)
            args.update(oauth)

        callback = self.async_callback(self._on_douban_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            headers = _to_header(args)
            headers['Content-Type'] = 'application/atom+xml; charset=utf-8'
            http.fetch(url, method="POST", headers=headers,
                    body=post_args, callback=callback)
        else:
            http.fetch(url_concat(url, args), callback=callback)

    def douban_saying(self, callback, access_token=None, content=None, **args):
        """ douban miniblog
        Example usage::
            
            class MainHandler(tornado.web.RequestHandler, DoubanMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                def get(self):
                    self.douban_saying(self.async_callback(self._on_saying),
                            access_token=user["access_token"], content="test content")

                def _on_saying(self, xml):
                    if not xml:
                        raise tornado.web.HTTPError(500, 'Douban saying failed')
                    self.write(xml)
                    self.finish()
        """
        path = "/miniblog/saying"
        if not access_token or not content:
            raise
        try: content = content.encode('utf-8')
        except UnicodeDecodeError: pass
        content = xhtml_escape(content)
        post_args = '<entry><content>%s</content></entry>' % content
        self.douban_request(path, callback, access_token, post_args, **args)

    def _on_douban_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                    response.request.url)
            callback(None)
            return
        callback(response.body)

    def _oauth_consumer_token(self):
        self.require_setting("douban_consumer_key", "Douban OAuth")
        self.require_setting("douban_consumer_secret", "Douban OAuth")
        token = dict(key=self.settings["douban_consumer_key"],
                secret=self.settings["douban_consumer_secret"])
        return token

    def _oauth_get_user(self, access_token, callback):
        callback = self.async_callback(self._parse_user_response, callback)
        self.douban_request("/people/%40me",
                access_token=access_token, callback=callback)


    def _parse_user_response(self, callback, xml):
        user = {}
        _uid = re.findall(r'<db:uid>(\S+?)</db:uid>', xml)
        _nick = re.findall(r'<title>(.*?)</title>', xml)
        _loc = re.findall(r'<db:location\s+id="(\S+?)">', xml)
        _avatar = re.findall(r'<link\s+href="(\S+?)"\s+rel="icon"', xml)
        if _uid:
            user['uid'] = _uid[0]
        if _nick:
            user['nickname'] = _nick[0]
        if _loc:
            user['location'] = _loc[0]
        if _avatar:
            user['avatar'] = _avatar[0]
        callback(user)

def _to_header(kw):
    s = ", ".join(['%s="%s"' % (k, _quote(v)) for k, v in kw.iteritems() if k.startswith('oauth_')])
    h = 'OAuth realm="", %s' % s
    return {'Authorization': h}

def _quote(s):
    return urllib.quote(str(s), '~')
