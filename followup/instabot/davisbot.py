#!/usr/bin/env python/
# -*- coding: utf-8 -*-

import time
from InstagramAPI import InstagramAPI
from instabot import InstaBot
import datetime
import signal
import sys
import csv
import random
import os
import wget
import cPickle as pickle


def getPastFollowed(pickle_file,pages):
    if os.path.isfile(pickle_file):
        following, max_id = pickle.load(open(pickle_file,'rb'))
        for page in pages:
            if page not in max_id.keys():
                max_id[page] = ''
    else:
        following = list()
        max_id = dict((el,'') for el in pages)

    return following,max_id


def getUploadList(upload_file):
    reader = csv.reader(upload_file)
    my_list = list(reader)
    upload_list = list()
    for lis in my_list:
        for obj in lis:
            upload_list.append(obj)
    return upload_list


class Bot():

    def __init__(self,username,password,pages,likes_per_day, \
		follows_per_day,pickle_file,uploads_per_day=None, \
		caption=None,pic_path=None,scrape_user=None,upload_file=None):
        self.following, self.max_id = getPastFollowed(pickle_file,pages)
        signal.signal(signal.SIGINT, self.signal_handler)
        self.last_like = self.last_follow = time.time()
        self.start_time = datetime.datetime.now()
        self.pages = pages
        self.follows_per_day = follows_per_day
        self.like_wait = (1.0/float(likes_per_day/57600.0))
        self.follow_wait = (1.0/float(self.follows_per_day/57600.0))
        self.user_followers = list()
        self.page_iter = -1
        self.follow_iter = self.like_iter = 0
        self.pickle_file = pickle_file
        self.unfollowing = False
        self.whitelist = list()
        self.uploads_per_day = uploads_per_day
        if self.uploads_per_day is not None:
            self.uploadSetup(uploads_per_day,uploadFile,\
                            scrape_user,caption,pic_path)
        self.poster = InstaBot(username,password)
        self.getter = InstagramAPI(username,password) 
        self.getter.login()

    def uploadSetup(self):
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


    def getWhiteList(self,make,whitelist):
	'''
        If make is True, will make 

	a new whitelist of all your 

	current followings, else it 

	will load the user defined whitelist file
	'''
        if make:
            self.whitelist=list()
            followings = self.getter.getTotalSelfFollowings()
            for user in followings:
                self.whitelist.append(user['pk'])
            pickle.dump(self.whitelist,open(whitelist,'wb'))
        else:
            self.whitelist = pickle.load(open(whitelist,'rb'))


    def loop(self):
        '''
        Constant loop of liking,

        following, and unfollowing

        of users
        '''
        while True:
            #time elapsed since unfollow event
            time_elapsed = datetime.datetime.now()-self.start_time 
            # Waiting to begin loop after unfollowing
            if time_elapsed >= datetime.timedelta(hours=8) \
                    and self.unfollowing:
                self.start_time  = datetime.datetime.now()
                self.unfollowing = False
            # Waiting to begin unfollowing after loop
            elif time_elapsed >= datetime.timedelta(hours=16):
                self.start_time = datetime.datetime.now()
                self.unfollow()
            # Looping
            else:
                if not self.user_followers or \
                        self.follow_iter >= \
                        len(self.user_followers['users']):
                    self.scrape_users()
                    self.follow_iter = 0
                if self.like_iter >= len(self.user_followers['users']):
                    self.like_iter = 0
                # Like
                if (time.time()-self.last_like) / \
                        self.like_wait >= 1:
                    self.like()
                # Follow 
                if (time.time() - self.last_follow) / \
                        self.follow_wait >= 1:
                    self.follow()
                # Upload 
                if self.uploads_per_day is not None and \
                        (time.time() - self.last_upload) / \
                        self.upload_wait >=1:
                    self.upload()

    def scrape_users(self):
        '''Scrapes users from a particular page'''
        if self.page_iter < len(self.pages)-1:
            self.page_iter += 1
        else:
            self.page_iter = 0
        success = self.getter.searchUsername(\
                    self.pages[self.page_iter])
        print('Scraping from %s' % (self.pages[self.page_iter]))
        user_id = self.getter.LastJson
        if success:
            success = self.getter.getUserFollowers( \
                        user_id['user']['pk'], \
                        self.max_id[self.pages[self.page_iter]])
            if success:
                self.user_followers = self.getter.LastJson
                if self.user_followers['big_list']:
                    self.max_id[self.pages[self.page_iter]] = \
                            self.user_followers['next_max_id']
                else:
                    self.max_id[self.pages[self.page_iter]] = ''
                print('Follower list is %s followers long' % \
                        (len(self.user_followers['users'])))
                pickle.dump((self.following,self.max_id), \
                            open(self.pickle_file,'wb'))

    def like(self):
        '''Likes first media of user'''
        if self.user_followers['users']\
                [self.like_iter]['is_private']:
            self.like_iter += 1
        else:
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
                        self.like_iter += 1
                    else:
                        print("Like request returned %s. Trying again" % req.status_code)
                        time.sleep(5)

                else:
                    self.like_iter += 1

    def follow(self):
        ''' Follows scraped user'''
        if self.user_followers['users'][self.follow_iter]['pk'] \
                in self.following:
            self.follow_iter += 1
        else:
            req = self.poster.follow(\
                        self.user_followers['users']\
                        [self.follow_iter]['pk'])
            if req.status_code == 200:
                self.last_follow = time.time()
                print('Followed %s' % \
                        (self.user_followers['users']\
                        [self.follow_iter]['username']))
                self.following.append(\
                        self.user_followers['users']\
                        [self.follow_iter]['pk'])
                pickle.dump((self.following,self.max_id),\
                            open(self.pickle_file,'wb'))
                self.follow_iter += 1
            else:
                print("Follow request returned %s. Trying again" % req.status_code)
                time.sleep(5)

    def unfollow(self):
        '''Unfollows all people not on whitelist'''
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

    def signal_handler(self,signal,frame):
        '''SIGINT signal to start unfollowing before quitting'''
        pickle.dump((self.following,self.max_id),\
                open(self.pickle_file,'wb'))
        self.getter.logout()
        self.poster.logout()
        sys.exit(0)
