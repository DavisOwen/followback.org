# -*- coding: utf-8 -*-

import json
import sys
if 'threading' in sys.modules:
    del sys.modules['threading']
import requests

class NotLoggedIn(Exception):
    pass

class Poster:
    url = 'https://www.instagram.com/'
    url_likes = 'https://www.instagram.com/web/likes/%s/like/'
    url_unlike = 'https://www.instagram.com/web/likes/%s/unlike/'
    url_comment = 'https://www.instagram.com/web/comments/%s/add/'
    url_follow = 'https://www.instagram.com/web/friendships/%s/follow/'
    url_unfollow = 'https://www.instagram.com/web/friendships/%s/unfollow/'
    url_login = 'https://www.instagram.com/accounts/login/ajax/'
    url_logout = 'https://www.instagram.com/accounts/logout/'
    user_agent = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36")
    accept_language = 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4'
    login_status = False

    def __init__(self,
                 login,
                 password):

        self.s = requests.Session()
        self.user_login = login.lower()
        self.user_password = password

    def try_login(self):

        self.s.cookies.update({
            'sessionid': '',
            'mid': '',
            'ig_pr': '1',
            'ig_vw': '1920',
            'csrftoken': '',
            's_network': '',
            'ds_user_id': ''
        })
        self.login_post = {
            'username': self.user_login,
            'password': self.user_password
        }
        self.s.headers.update({
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': self.accept_language,
            'Connection': 'keep-alive',
            'Content-Length': '0',
            'Host': 'www.instagram.com',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
            'User-Agent': self.user_agent,
            'X-Instagram-AJAX': '1',
            'X-Requested-With': 'XMLHttpRequest'
        })
        r = self.s.get(self.url)
        self.s.headers.update({'X-CSRFToken': r.cookies['csrftoken']})
        login = self.s.post(
            self.url_login, data=self.login_post, allow_redirects=True)
        self.s.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
        self.csrftoken = login.cookies['csrftoken']

        if login.status_code == 200:
            r = self.s.get('https://www.instagram.com/')
            finder = r.text.find(self.user_login)
            if finder != -1:
                self.login_status = True
                return_code=0
            else:
                self.login_status = False
                return_code=1
        else:
            login_json = login.json()
            if login_json['message'] == 'checkpoint_required':
                checkpoint_url = login_json
                checkpoint_url = checkpoint_url['checkpoint_url']
                checkpoint_url = self.url+checkpoint_url[1:]
                checkpoint = self.s.post(checkpoint_url, 
                                        data={'choice':'1'}, 
                                        allow_redirects=True)
                login = checkpoint
                return_code=2
            else:
                return_code=4
        login = login.json()
        return (return_code,self.s,login)

    def login(self,cookies,headers):
        self.s.cookies.update(cookies)
        self.s.headers.update(headers)
        self.csrftoken = self.s.headers['X-CSRFToken']
        self.login_status = True

    def handle_checkpoint(self,code,cookies,headers,response):
        self.s.cookies.update(cookies)
        self.s.headers.update(headers)
        security_code = code
        checkpoint_url = self.url+response['navigation']['forward'][1:]
        checkpoint = self.s.post(checkpoint_url,
                                data={'security_code':security_code},
                                allow_redirects=True)
        if checkpoint.status_code == 200:
            self.s.headers.update({'X-CSRFToken': checkpoint.cookies['csrftoken']})
            self.csrftoken = checkpoint.cookies['csrftoken']
            r = self.s.get("https://www.instagram.com/")
            finder = r.text.find(self.user_login)
            if finder != -1:
                self.login_status = True
                return_code=0
            else:
                self.login_status = False
                return_code= 1
        else:
            self.login_status = False
            return_code=3

        return (return_code,self.s)

    def logout(self):
        try:
            logout_post = {'csrfmiddlewaretoken': self.csrftoken}
            logout = self.s.post(self.url_logout, data=logout_post)
            self.login_status = False
        except:
            pass

    def like(self, media_id):
        """ Send http request to like media by ID """
        if self.login_status:
            url_likes = self.url_likes % (media_id)
            like = self.s.post(url_likes)
            return like
        else:
            raise NotLoggedIn()

    def unlike(self, media_id):
        """ Send http request to unlike media by ID """
        if self.login_status:
            url_unlike = self.url_unlike % (media_id)
            unlike = self.s.post(url_unlike)
            return unlike
        else:
            raise NotLoggedIn()

    def comment(self, media_id, comment_text):
        """ Send http request to comment """
        if self.login_status:
            comment_post = {'comment_text': comment_text}
            url_comment = self.url_comment % (media_id)
            comment = self.s.post(url_comment, data=comment_post)
            return comment
        else:
            raise NotLoggedIn()

    def follow(self, user_id):
        """ Send http request to follow """
        if self.login_status:
            url_follow = self.url_follow % (user_id)
            follow = self.s.post(url_follow)
            return follow
        else:
            raise NotLoggedIn()

    def unfollow(self, user_id):
        """ Send http request to unfollow """
        if self.login_status:
            url_unfollow = self.url_unfollow % (user_id)
            unfollow = self.s.post(url_unfollow)
            return unfollow
        else:
            raise NotLoggedIn()
