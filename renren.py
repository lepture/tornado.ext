#!/usr/bin/env python

import logging
import urllib
from tornado import httpclient
from tornado.escape import json_decode
from tornado.httputil import url_concat


class RenrenGraphMixin(object):
    _OAUTH_AUTHORIZE_URL = "https://graph.renren.com/oauth/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://graph.renren.com/oauth/token"

    _API_URL = 'http://api.renren.com/restserver.do'

    def authorize_redirect(self, redirect_uri, response_type='code', scope=None, **args):
        consumer_token = self._oauth_consumer_token()
        all_args = {
            'client_id': consumer_token['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': response_type,
        }
        if scope: all_args.update({'scope': scope})
        args.update(all_args)
        self.redirect(url_concat(self._OAUTH_AUTHORIZE_URL, args))
    
    def get_authenticated_user(self, callback):
        #TODO
        pass

    def renren_request(self, path, args):
        #TODO
        pass

    def get_access_token(self, callback, code, grant_type='code', redirect_uri=None):
        if grant_type == 'refresh_token':
            args = {
                'grant_type': 'refresh_token',
                'refresh_token': code,
            }
        elif redirect_uri:
            args = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
            }
        else:
            logging.error('Renren Get Access Token Error. redirect_uri required')
            return
        args.update(self._oauth_consumer_token())

        callback = self.async_callback(self._on_get_access_token, callback)
        http = httpclient.AsyncHTTPClient()
        http.fetch(self._OAUTH_ACCESS_TOKEN_URL, method="POST",
                   body=urllib.urlencode(args), callback=callback)

    def _on_get_access_token(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                    response.request.url)
            callback(None)
            return
        res = json_decode(response.body)
        if 'error' in res:
            logging.warning("Error response %s fetching %s", res['error_description'],
                    response.request.url)
            callback(None)
            return
        callback(res)

    def _oauth_consumer_token(self):
        self.require_setting("renren_client_id", "Renren Client ID")
        self.require_setting("renren_client_secret", "Renren Client Secret")
        token = dict(key=self.settings["client_id"],
                     secret=self.settings["client_secret"])
        return token

