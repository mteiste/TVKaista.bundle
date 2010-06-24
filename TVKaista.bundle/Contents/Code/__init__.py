# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

import feedparser

VIDEO_PREFIX = "/video/tvkaista"
ROOT_URL	= "http://www.tvkaista.fi/feed/"

NAME = L('Title')
ART		= 'art-default.png'
ICON	= 'icon-default.png'

def Start():
	Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

	MediaContainer.art = R(ART)
	MediaContainer.title1 = NAME
	DirectoryItem.thumb = R(ICON)

def VideoMainMenu():
	try:
		dir = getMenu(sender=None, url=ROOT_URL)
		
		dir.Append( # Movie dir
			Function(
				DirectoryItem(
					getMenu,
					L('MoviesTitle'),
					subtitle=L('MoviesSub'),
					summary=L('MoviesSum') 
				), url="http://tvkaista.fi/feed/search/title/elokuva"
			)
		)
		
		dir.Append(
			Function(
				InputDirectoryItem(
					SearchMenu,
					L('SearchTitle'),
					L('SearchSub'),
					summary=L('SearchSum'),
					thumb=R(ICON),
					art=R(ART)
				)
			)
		)
		
	except: # Displays settings when listing fails
		dir = MediaContainer(viewGroup="InfoList")
		
	dir.Append(
		PrefsItem(
			title=L('Settings'),
			subtile=L('SettingsSub'),
			summary=L('SettingsSum'),
			thumb=R(ICON)
		)
	)

	return dir

# Directory listing
def getMenu(sender, url):
	dir = MediaContainer(viewGroup="InfoList")
	
	url = authURL(url) # Add authentication to url
	feed = feedparser.parse(url)

	if feed['feed']['description'].find("Media RSS") == 0: # Video listing
		if url[len(url) - 1] != '/':
			url = url + '/'	
		url = url + Prefs.Get('format') + ".rss"
		feed = feedparser.parse(url)
		
		for entry in feed.entries:
			try:
				dir.Append(VideoItem(authURL(entry.enclosures[0].url), entry.title, subtitle=entry.date, summary=entry.description))
			except: # Missing info doesn't stop listing
				Log(entry.title + "-> missing information")
						
	else: # Directory
		for entry in feed.entries:
			if entry.title != 'Search':
				dir.Append(
					Function(
						DirectoryItem(
							getMenu,
							entry.title,
							subtitle=entry.description
						), url=entry.link
					)	
				)
		
	return dir
	
def SearchMenu(sender,query=None):
	search = query.replace (' ', '+')
	return getMenu(sender=None, url="http://tvkaista.fi/feed/search/title/" + search)
	
def authURL(url):
	url = "http://" + Prefs.Get('username') + ":" + Prefs.Get('password') + '@' + url.split("http://")[1]

	return url
