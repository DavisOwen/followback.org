# -*- coding: utf-8 -*-

from getter import Getter
from poster import Poster
from followback import db
from followback.models import InstaUser, Whitelist, Followed, MaxID
from followback.views import celery_logger as logger
import time
import datetime
import random
import os
import traceback
import signal
import sys
#import wget


#def getUploadList(upload_file):
#    reader = csv.reader(upload_file)
#    my_list = list(reader)
#    upload_list = list()
#    for lis in my_list:
#        for obj in lis:
#            upload_list.append(obj)
#    return upload_list

'''

Instagram Bot for the followback application

Needs username, password, pages to scrape, max follows per day, max likes per day

Note: poster and getter refer to two separate instagramAPI's. The poster is used for 

post requests, such as liking, following, and unfollowing. The getter is for get requests,

such as scraping users. The poster is simply interacting via requests directly to instagram.com

via http, and the getter is using instagrams private api. The tradeoff lies in the fact that the 

private api does not like very many requests per day, whereas the http requests one can do many more.

However, the http api does not allow one to scrape users from profiles.

'''

class InstagramBot:

    def __init__(self,args):
        self.username = args['username']
        self.password = args['password']
        self.pages = args.get('pages',None)
        self.follows_per_day = args.get('follows_per_day',1)
        likes_per_day = args.get('likes_per_day',1)
        self.use_whitelist = args.get('use_whitelist',True)
        self.uploads_per_day = args.get('uploads_per_day',None)
        caption = args.get('caption',None)
        pic_path = args.get('pic_path',None)
        scrape_user = args.get('scrape_user',None)
        upload_file = args.get('upload_file',None)
        self.like_wait = (1.0/float(likes_per_day/57600.0))
        self.follow_wait = (1.0/float(self.follows_per_day/57600.0))
        self.user_followers = list()
        self.page_iter = -1
        self.errors = 0
        self.follow_iter = self.like_iter = 0
        self.unfollowing = False
        if self.uploads_per_day is not None:
            self.upload_setup(self.uploads_per_day,uploadFile,\
                            scrape_user,caption,pic_path)

    def set_up(self):
        '''
        Gets user, all past followers

        the max_id status of each page, 
        
        and the users whitelist
        '''
        self.user = self.get_user(self.username)
        self.following = self.get_followed()
        self.max_id = self.get_max_id(self.pages)
        self.whitelist = self.get_whitelist(self.use_whitelist)

    def try_login_poster(self):
        '''
        Try logging into the

        poster
        '''
        self.poster = Poster(self.username,self.password)
        status = self.poster.try_login()
        return status

    def login_poster(self,cookies,headers):
        ''' 
            Requires header 
        
            and cookie data 

            from login.

            Will login poster
        '''
        self.poster = Poster(self.username,self.password)
        self.poster.login(cookies,headers)

    def handle_checkpoint_poster(self,code,cookies,headers,response):
        '''
        Handles the checkpoint situation
        '''
        self.poster = Poster(self.username,self.password)
        status = self.poster.handle_checkpoint(code,cookies,headers,response)
        return status

    def login_getter(self):
        '''
        Logs into getter,

        should have no problems
        
        if one can log into poster
        '''
        self.getter = Getter(self.username,self.password)
        status = self.getter.login()
        return status

    def get_user(self,username):
        '''
        Gets the insta user

        with its history from 

        the database
        '''
        user = InstaUser.query.filter_by(username=username).first()
        return user

    def get_followed(self):
        '''
        Gets all people previously

        followed by the insta user
        '''
        followed = [ x.pk for x in self.user.followed ]
        return followed

    def get_max_id(self,pages):
        '''
        Gets the max_id's for each page

        of the current bot instance
        '''
        if not pages:
            return None
        max_id = dict((el.page,el.max_id) for el in self.user.max_id)
        for page in pages:
            if page not in max_id.keys():
                max_id[page] = ''
                max_id_model = MaxID(page=page,max_id='')
                self.user.max_id.append(max_id_model)
                db.session.add(self.user)
                db.session.commit()
        return max_id

    def get_whitelist(self,use_whitelist):
	'''
	Load the whitelist if use_whitelist is True 
	'''
        if use_whitelist:
            whitelist = [ x.pk for x in self.user.whitelist ]
        else:
            whitelist = list()
        return whitelist

    def upload_setup(self):
        '''Creates variables needed for upload'''
        self.upload_wait = 1.0/float(self.uploads_per_day/57600.0)
        self.upload_file = open(uploadFile,'a+')
        self.scrape_user = scrape_user
        self.scrape_media()
        self.caption = caption
        self.pic_path = pic_path
        self.last_upload = time.time()
        self.photo_iter = 0
        self.upload_list = getUploadList(upload_file) 

    def loop(self,state,start_time):
        '''
        Constant loop of liking,

        of users
        '''

        class SignalHandler(object):
            def __init__(self,bot):
                self.retval = None
            def signal_handler(self, sig, frm):
                self.retval = True

        class BotStop(Exception):
            pass

        class ProbablyBanned(Exception):
            pass

        s = SignalHandler(self)
        signal.signal(signal.SIGINT, s.signal_handler)
        self.likes = 0
        self.follows = 0
        self.last_like = self.last_follow = time.time()
        start_time = start_time
        halt = False
        while True:
            try:
                if s.retval:
                    logger.warning('Bot stopped by user')
                    raise BotStop()
                if self.errors >= 10:
                    logger.error('Probably banned')
                    raise ProbablyBanned()
                #time elapsed since unfollow event
                time_elapsed = datetime.datetime.utcnow()-start_time 
                # Waiting to begin loop after unfollowing
                if time_elapsed >= datetime.timedelta(hours=8) \
                        and self.unfollowing:
                    start_time  = datetime.datetime.utcnow()
                    self.unfollowing = False
                # Waiting to begin unfollowing after loop
                elif time_elapsed >= datetime.timedelta(hours=16):
                    start_time = datetime.datetime.utcnow()
                    self.unfollow()
                # Looping
                else:
                    if not self.user_followers or self.follow_iter \
                            >= len(self.user_followers['users']):
                        success = self.scrape_users()
                        if success:
                            self.follow_iter = 0
                            halt = False
                        else:
                            halt = True
                    if not halt:
                        if self.like_iter >= len(self.user_followers['users']):
                            self.like_iter = 0
                        # Like
                        if (time.time()-self.last_like) / \
                                self.like_wait >= 1:
                            self.like()
                            state.update_state(state="PROGRESS",
                                        meta={"type":"bot",
                                            "likes":self.likes,
                                            "follows":self.follows,
                                            "start_time":start_time,
                                            "end_time":0})

                        # Follow 
                        if (time.time() - self.last_follow) / \
                                self.follow_wait >= 1:
                            self.follow()
                            state.update_state(state="PROGRESS",
                                    meta={"type":"bot",
                                        "likes":self.likes,
                                        "follows":self.follows,
                                        "start_time":start_time,
                                        "end_time":0})

                        # Upload 
                        if self.uploads_per_day is not None and \
                                (time.time() - self.last_upload) / \
                                self.upload_wait >=1:
                            self.upload()
            except Exception as e:
                if isinstance(e, BotStop):
                    results = dict({"state":"STOPPED","type":"bot","likes":self.likes,
                                "follows":self.follows,"start_time":start_time,
                                "end_time":datetime.datetime.utcnow()})
                elif isinstance(e, ProbablyBanned):
                    results = dict({"state":"BANNED","type":"bot","likes":self.likes,
                                "follows":self.follows,"start_time":start_time,
                                "end_time":datetime.datetime.utcnow()})
                else:
                    logger.error(e)
                    logger.error(traceback.format_exc())
                    results = dict({"state":"ERROR","type":"bot","likes":self.likes,
                                "follows":self.follows,"start_time":start_time,
                                "end_time":datetime.datetime.utcnow()})
                db.session.add(self.user)
                db.session.commit()
                self.getter.logout()
                self.poster.logout()
                return results

    def scrape_users(self):
        '''Scrapes users from a particular page'''

        def addMaxID(page,max_id):
            for el in self.user.max_id:
                if el.page == page:
                    el.max_id = max_id
            db.session.add(self.user)
            db.session.commit()

        if self.page_iter < len(self.pages)-1:
            self.page_iter += 1
        else:
            self.page_iter = 0
        page = self.pages[self.page_iter]
        logger.info('Scraping from %s' % (page))
        req = self.getter.searchUsername(page)
        user_id = self.getter.LastJson
        if req.status_code == 200:
            if user_id['user']['is_private']:
                self.errors += 1 
                self.page_iter += 1
                logger.warning('User %s is private, trying next page' % page)
                time.sleep(5)
                return False
            self.errors = 0
            req = self.getter.getUserFollowers( \
                        user_id['user']['pk'], \
                        self.max_id[page])
            if req.status_code == 200:
                self.errors = 0
                self.user_followers = self.getter.LastJson
                try:
                    isBigList = self.user_followers['big_list']
                    if self.user_followers['big_list']:
                        self.max_id[page] = \
                                self.user_followers['next_max_id']
                        addMaxID(page,self.user_followers['next_max_id'])
                    else:
                        self.max_id[page] = ''
                        addMaxID(page,'')
                except:
                    self.max_id[page] = ''
                    addMaxID(page,'')
                return True
            else:
                logger.error("Returned %s. Could not get %s's followers" % (req.status_code,page))
                logger.error(req.text)
                try:
                    logger.error(req.json())
                except:
                    pass
                self.errors += 1
                time.sleep(5)
                return False
        else:
            logger.error("Returned %s. Could not find user %s, retrying" % (req.status_code,page))
            logger.error(req.text)
            try:
                logger.error(req.json())
            except:
                pass
            self.errors += 1
            time.sleep(5)
            return False

    def like(self):
        '''Likes first media of user'''
        req = self.getter.getUserFeed(\
                self.user_followers['users']\
                [self.like_iter]['pk'])
        if req.status_code == 200:
            self.errors = 0
            user_feed = self.getter.LastJson
            if user_feed['num_results'] > 0:
                req = self.poster.like(\
                        user_feed['items'][0]['pk'])
                if req.status_code == 200:
                    self.errors = 0
                    self.last_like = time.time()
                    logger.info("Liked %s\'s media" % \
                             (self.user_followers['users']\
                            [self.like_iter]['username']))
                    self.likes += 1
                    self.like_iter += 1
                else:
                    logger.error("Like request returned %s for user %s. Trying next user" %
                                    req.status_code,self.user_followers['users']
                                    [self.like_iter]['username'])
                    logger.error(req.text)
                    try:
                        logger.error(req.json())
                    except:
                        pass
                    self.errors += 1
                    self.like_iter += 1
                    self.last_like = time.time()
            else:
                self.like_iter += 1
        else:
            logger.error("Could not get %s\'s feed. Trying next user" %
                            self.user_followers['users'][self.like_iter]['username'])
            logger.error(req.text)
            try:
                logger.error(req.json())
            except:
                pass
            self.errors += 1
            self.like_iter += 1
            self.last_like = time.time()

    def follow(self):
        ''' Follows scraped user'''
        user = self.user_followers['users'][self.follow_iter]['pk']
        if user in self.following:
            self.follow_iter += 1
        else:
            req = self.poster.follow(user)
            if req.status_code == 200:
                self.errors = 0 
                logger.info("Followed %s" % 
                                self.user_followers['users'][self.follow_iter]['username'])
                self.last_follow = time.time()
                self.following.append(user)
                followed = Followed(pk=user)
                self.user.followed.append(followed)
                db.session.add(self.user)
                db.session.commit()
                self.follows += 1
                self.follow_iter += 1
            else:
                logger.error("Follow request for %s returned %s. Trying next user" %
                                (self.user_followers['users'][self.follow_iter]['username'],req.status_code))
                logger.error(req.text)
                try:
                    logger.error(req.json())
                except:
                    pass
                self.errors += 1
                self.follow_iter += 1
                self.last_follow = time.time()

    def unfollow(self,state=None,start_time=None):
        '''Unfollows all people not on whitelist'''
        logger.info("Unfollowing")
        followings_obj = self.getter.getTotalSelfFollowings()
        followings=list()
        unfollows = 0
        for user in followings_obj:
           followings.append(user['pk']) 
        for user in followings:
            if user not in self.whitelist:
                req = self.poster.unfollow(user)
                if req.status_code == 200:
                    logger.info("Unfollowed %s" % (user))
                    if state:
                        unfollows += 1
                        state.update_state(state="PROGRESS",
                                        meta={"type":"unfollow",
                                            "unfollows":unfollows,
                                            "start_time":start_time,
                                            "end_time":0})
                    time.sleep(28800/self.follows_per_day)
                else:
                    logger.error("Unfollowed %s failed, trying next user" % (user))
                    logger.error(req.text)
                    try:
                        logger.error(req.json())
                    except:
                        pass
                    self.errors += 1
                    time.sleep(5)
        if state:
            results = dict({"state":"FINISHED","type":"unfollow",
                                "unfollows":unfollows,
                                "start_time":start_time,
                                "end_time":datetime.datetime.utcnow()})
        self.unfollowing = True

    def scrape_media(self):
        '''Scrapes media from page (photos)'''
        success = self.getter.searchUsername(self.scrape_user)
        if success:
            user = self.getter.LastJson	
            self.media_count = user['user']['media_count']
            print('Scraped media from %s' % (self.scrape_user))
            self.feed = self.getter.getTotalUserFeed(user['user']['pk'])
        else:
            time.sleep(5)
            scrape_media()

    def upload(self):
        '''Uploads media'''
        # Uploads media from file
        if self.scrape_user is None:
            if os.listdir(self.pic_path):
                ListFiles = [f for f in os.listdir(self.pic_path)]
                photo = ListFiles[0]
                photo_dir = os.path.join(self.pic_path,photo)
                success = self.getter.uploadPhoto(photo_dir, \
                        caption=self.caption,upload_id=None)
                if success:
                    self.last_upload = time.time()
                    print('Uploaded photo')
                    os.remove(photo_dir)
        # Uploads scraped media
        else:
            caption = str()
            rnd = random.randint(0,self.media_count-1)
            if self.feed[rnd]['media_type'] == 1 and \
                    self.feed[rnd]['pk'] not in self.upload_list:
                media = wget.download( \
                        self.feed[rnd]['image_versions2']\
                        ['candidates'][0]['url'])
                if self.feed[rnd]['caption'] is not None and self.caption:
                    caption = self.feed[rnd]['caption']['text']
                elif self.caption is None:
                    self.caption = str()
                caption += ' '+self.caption
                success = self.getter.uploadPhoto(media, \
                        caption=caption,upload_id=None)
                if success:
                    self.last_upload = time.time()
                    print('Scraped and uploaded photo')
                    os.remove(media)
                    self.upload_list.append(self.feed[rnd]['pk'])
                    self.upload_file.write(str(self.feed[rnd]['pk'])+',')