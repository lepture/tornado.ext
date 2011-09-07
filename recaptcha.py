#!/usr/bin/env python

import logging
import urllib

from tornado.auth import httpclient

class RecaptchaMixin(object):
    """
    Example usage::

        class SignupHandler(BaseHandler, RecaptchaMixin):
            def get(self):
                if self.current_user:
                    return self.redirect('/')
                form = SignupForm()
                recaptcha = self.recaptcha_render()
                return self.render('auth/signup.html', form=form, recaptcha=recaptcha)

            @asynchronous
            def post(self):
                form = SignupForm(self.request.arguments)
                if form.validate():
                    user = form.save()
                    user.signup_ip = user.signin_ip = self.request.remote_ip
                    self.recaptcha_validate(self.async_callback(self._on_validate, user))
                    return

                recaptcha = self.recaptcha_render()
                html = self.render_string('auth/signup.html', form=form, recaptcha=recaptcha)
                self.write(html)
                self.finish()

            def _on_validate(self, user, response):
                if not response:
                    form = SignupForm(self.request.arguments)
                    recaptcha = self.recaptcha_render()
                    html = self.render_string('auth/signup.html', form=form, recaptcha=recaptcha)
                    self.write(html)
                    self.finish()
                    return
                self.db.add(user)
                self.db.commit()
                self.set_secure_cookie('user', user.email)
                return self.redirect('/')
    """
    RECAPTCHA_VERIFY_URL = "http://www.google.com/recaptcha/api/verify"

    def recaptcha_render(self):
        token = self._recaptcha_token()
        html = u'<div id="recaptcha_div"></div>'
        html += u'<script type="text/javascript" src="http://www.google.com/recaptcha/api/js/recaptcha_ajax.js"></script>'
        s = u'<script type="text/javascript">Recaptcha.create("%(key)s", "recaptcha_div", {theme: "%(theme)s",callback: Recaptcha.focus_response_field});</script>'
        html += s % token
        return html

    def recaptcha_validate(self, callback):
        token = self._recaptcha_token()
        challenge = self.get_argument('recaptcha_challenge_field', None)
        response = self.get_argument('recaptcha_response_field', None)
        callback = self.async_callback(self._on_recaptcha_request, callback)
        http = httpclient.AsyncHTTPClient()
        post_args = {
            'privatekey': token['secret'],
            'remoteip': self.request.remote_ip,
            'challenge': challenge,
            'response': response
        }
        http.fetch(self.RECAPTCHA_VERIFY_URL, method="POST",
                   body=urllib.urlencode(post_args), callback=callback)

    def _on_recaptcha_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                    response.request.url)
            callback(None)
            return
        verify, message = response.body.split()
        if verify == 'true':
            callback(response.body)
        else:
            logging.warning("Recaptcha verify failed %s", message)
            callback(None)


    def _recaptcha_token(self):
        self.require_setting("recaptcha_public_key", "Recaptcha Public Key")
        self.require_setting("recaptcha_private_key", "Recaptcha Private Key")
        self.require_setting("recaptcha_theme", "Recaptcha Theme")
        token = dict(
            key=self.settings["recaptcha_public_key"],
            secret=self.settings["recaptcha_private_key"],
            theme=self.settings["recaptcha_theme"],
        )
        return token
