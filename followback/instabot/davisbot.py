# -*- coding: utf-8 -*-

import sys
from InstagramAPI import InstagramAPI
from instabot import InstaBot
from followback import db
from followback.models import InstaUser, Whitelist, Followed, MaxID
import time
import datetime
import random
import os
import traceback
#import wget


#def getPastFollowed(pickle_file,pages):
#    if os.path.isfile(pickle_file):
#        following, max_id = pickle.load(open(pickle_file,'rb'))
#        for page in pages:
#            if page not in max_id.keys():
#                max_id[page] = ''
#    else:
#        following = list()
#        max_id = dict((el,'') for el in pages)
#
#    return following,max_id
#
#
#def getUploadList(upload_file):
#    reader = csv.reader(upload_file)
#    my_list = list(reader)
#    upload_list = list()
#    for lis in my_list:
#        for obj in lis:
#            upload_list.append(obj)
#    return upload_list

class Bot():

    def __init__(self,args):
        self.username = args['username']
        self.password = args['password']
        self.pages = args['pages']
        make = args['make']
        self.follows_per_day = args['follows_per_day']
        likes_per_day = args['likes_per_day']
        self.uploads_per_day = args['uploads_per_day']
        caption = args['caption']
        pic_path = args['pic_path']
        scrape_user = args['scrape_user']
        upload_file = args['upload_file']
        self.user = self.get_user(self.username)
        self.following = self.get_followed()
        self.max_id = self.get_max_id(self.pages)
        self.whitelist = self.get_whitelist(make)
        self.like_wait = (1.0/float(likes_per_day/57600.0))
        self.follow_wait = (1.0/float(self.follows_per_day/57600.0))
        self.user_followers = list()
        self.page_iter = -1
        self.follow_iter = self.like_iter = 0
        self.unfollowing = False
        if self.uploads_per_day is not None:
            self.upload_setup(self.uploads_per_day,uploadFile,\
                            scrape_user,caption,pic_path)

    def try_login_poster(self):
        self.poster = InstaBot(self.username,self.password)
        status = self.poster.try_login()
        return status

    def login_poster(self,cookies,headers):
        ''' 
            Requires header 
        
            and cookie data 

            from login 
        '''
        self.poster = InstaBot(self.username,self.password)
        self.poster.login(cookies,headers)

    def handle_checkpoint_poster(self,code,cookies,headers,response):
        self.poster = InstaBot(self.username,self.password)
        status = self.poster.handle_checkpoint(code,cookies,headers,response)
        return status

    def login_getter(self):
        self.getter = InstagramAPI(self.username,self.password)
        status = self.getter.login()
        return status

    def get_user(self,username):
        user = InstaUser.query.filter_by(username=username).first()
        return user

    def get_followed(self):
        followed = [ x.pk for x in self.user.followed ]
        return followed

    def get_max_id(self,pages):
        max_id = dict((el.page,el.max_id) for el in self.user.max_id)
        for page in pages:
            if page not in max_id.keys():
                max_id[page] = ''
                max_id_model = MaxID(page=page,max_id='')
                self.user.max_id.append(max_id_model)
                db.session.add(self.user)
                db.session.commit()
        return max_id

    def get_whitelist(self,make):
	'''
        If make is True, will make 

	a new whitelist of all your 

	current followings, else it 

	will load the user defined whitelist file
	'''
        if make:
            whitelist=list()
            followings = self.getter.getTotalSelfFollowings()
            for user in followings:
                whitelist.append(user['pk'])
                pk = Whitelist(pk=user['pk'])
                self.user.whitelist.append(pk)
        else:
            whitelist = [ x.pk for x in self.user.whitelist ]

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
        self.likes = 0
        self.follows = 0
        self.last_like = self.last_follow = time.time()
        start_time = start_time
        while True:
            try:
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
                        self.scrape_users()
                        self.follow_iter = 0
                    if self.like_iter >= len(self.user_followers['users']):
                        self.like_iter = 0
                    # Like
                    if (time.time()-self.last_like) / \
                            self.like_wait >= 1:
                        self.like()
                        state.update_state(state="PROGRESS",
                                    meta={"likes":self.likes,
                                        "follows":self.follows,
                                        "start_time":start_time,
                                        "end_time":0})

                    # Follow 
                    if (time.time() - self.last_follow) / \
                            self.follow_wait >= 1:
                        self.follow()
                        state.update_state(state="PROGRESS",
                                    meta={"likes":self.likes,
                                        "follows":self.follows,
                                        "start_time":start_time,
                                        "end_time":0})

                    # Upload 
                    if self.uploads_per_day is not None and \
                            (time.time() - self.last_upload) / \
                            self.upload_wait >=1:
                        self.upload()
            except Exception as e:
                traceback.print_exc()
                state.update_state(state="ENDING",
                                    meta={"likes":self.likes,
                                        "follows":self.follows,
                                        "start_time":start_time,
                                        "end_time":datetime.datetime.utcnow()})
                db.session.add(self.user)
                db.session.commit()
                self.getter.logout()
                self.poster.logout()
                sys.exit(0)

    def scrape_users(self):
        '''Scrapes users from a particular page'''

        print('scraping users')
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
        success = self.getter.searchUsername(page)
        user_id = self.getter.LastJson
        if success:
            success = self.getter.getUserFollowers( \
                        user_id['user']['pk'], \
                        self.max_id[page])
            if success:
                self.user_followers = self.getter.LastJson
                if self.user_followers['big_list']:
                    self.max_id[page] = \
                            self.user_followers['next_max_id']
                    addMaxID(page,self.user_followers['next_max_id'])
                else:
                    self.max_id[page] = ''
                    addMaxID(page,'')

    def like(self):
        '''Likes first media of user'''
        success = self.getter.getUserFeed(\
                self.user_followers['users']\
                [self.like_iter]['pk'])
        if success:
            user_feed = self.getter.LastJson
            if user_feed['num_results'] > 0:
                req = self.poster.like(\
                        user_feed['items'][0]['pk'])
                if req.status_code == 200:
                    self.last_like = time.time()
                    print('Liked %s\'s media' % \
                            (self.user_followers['users']\
                            [self.like_iter]['username']))
                    self.likes += 1
                    self.like_iter += 1
                else:
                    print("Like request returned %s. Trying next user" % req.status_code)
                    self.like_iter += 1
                    time.sleep(5)
            else:
                self.like_iter += 1
        else:
            self.like_iter += 1
            time.sleep(5)

    def follow(self):
        ''' Follows scraped user'''
        user = self.user_followers['users'][self.follow_iter]['pk']
        if user in self.following:
            self.follow_iter += 1
        else:
            req = self.poster.follow(user)
            if req.status_code == 200:
                print('Followed %s' % user)
                self.last_follow = time.time()
                self.following.append(user)
                followed = Followed(pk=user)
                self.user.followed.append(followed)
                db.session.add(self.user)
                db.session.commit()
                self.follows += 1
                self.follow_iter += 1
            else:
                print("Follow request returned %s. Trying next user" % req.status_code)
                self.follow_iter += 1
                time.sleep(5)

    def unfollow(self):
        '''Unfollows all people not on whitelist'''
        print('Unfollowing for some reason')
        followings_obj = self.getter.getTotalSelfFollowings()
        followings=list()
        for user in followings_obj:
           followings.append(user['pk']) 
        for user in followings:
            if user not in self.whitelist:
                req = self.poster.unfollow(user)
                if req.status_code == 200:
                    print('Unfollowed %s' % (user))
                    time.sleep(28800/self.follows_per_day)
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
