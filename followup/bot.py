#!/usr/bin/python

import sys
from instabot import Bot

pickle_file = sys.argv[0][:-3]+'.pickle'
uploads_per_day = None
caption = None
pic_path = None
scrape_user = None
uploadFile = None

username = sys.argv[1]
password = sys.argv[2]
pages = sys.argv[3]
likes_per_day = sys.argv[4]
follows_per_day = sys.argv[5]

bot = Bot(username=username,password=password,pages=pages,likes_per_day=likes_per_day,follows_per_day=follows_per_day,pickle_file=pickle_file)#uploads_per_day,caption,pic_path,scrape_user,uploadFile)
bot.getWhiteList(make=False,whitelist='personalbot.whitelist')
bot.loop()
