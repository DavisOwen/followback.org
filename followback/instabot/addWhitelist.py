#!/usr/bin/python

from instabot import InstagramAPI
import sys
import cPickle as pickle
import time

class RequestFail(Exception):
    pass

user_id = 'davis_owen_guitar'
password = 'bdfaw472!'
addUsers = ['maxineparr6','melyssaperezzz']#add users as a list here
getter = InstagramAPI(user_id,password)
getter.login()
whitelist = pickle.load(open(sys.argv[1],'rb'))
for user in addUsers:
    for attempt in range(5):
        try:
            success = getter.searchUsername(user)
            if success:
                user_id = getter.LastJson
                user_id = user_id['user']['pk']
                whitelist.append(user_id)
                print('User %s successfully added' % (user))
            else:
                raise RequestFail('Request for user %s Failed' % (user))
        except RequestFail:
            time.sleep(5)
            continue
        break

pickle.dump(whitelist,open('personalbot.whitelist','wb'))
