# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

import feedparser

from email.utils import formatdate
from calendar import timegm


VIDEO_PREFIX	= "/video/tvkaista"
ROOT_URL	= "http://www.tvkaista.fi/feedbeta/"

NAME	= L('Title')
ART		= 'art-default.png'
ICON	= 'icon-default.png'

def Start():
	Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('VideoTitle'), ICON, ART)
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

	MediaContainer.art = R(ART)
	MediaContainer.title1 = NAME
	DirectoryItem.thumb = R(ICON)

def MainMenu():
	dir = MediaContainer(viewGroup="InfoList")
		
	dir.Append(
		Function(
			DirectoryItem(
				getMenu,
				L('ChannelsTitle'),
				subtitle=L('ChannelsSub'),
				summary=L('ChannelsSum')
			), url=ROOT_URL+"channels/"
		)
	)
	
	dir.Append(
		Function(
			DirectoryItem(
				getMenu,
				L('SeasonsTitle'),
				subtitle=L('SeasonsSub'),
				summary=L('SeasonsSum')
			), url=ROOT_URL+"seasonpasses/"
		)
	)
	
	dir.Append(
		Function(
			DirectoryItem(
				getMenu,
				L('PlaylistTitle'),
				subtitle=L('PlaylistSub'),
				summary=L('PlaylistSum')
			), url=ROOT_URL+"playlist/"
		)
	)
	
	dir.Append(
		Function(
			DirectoryItem(
				getMenu,
				L('PopularTitle'),
				subtitle=L('PopularSub'),
				summary=L('PopularSum')
			), url=ROOT_URL+"programs/popular/"
		)
	)

	dir.Append(
		Function(
			DirectoryItem(
				getMenu,
				L('MoviesTitle'),
				subtitle=L('MoviesSub'),
				summary=L('MoviesSum') 
			), url=ROOT_URL+"search/title/elokuva"
		)
	)
			
	dir.Append(
		Function(
			InputDirectoryItem(
				SearchMenu,
				L('SearchTitle'),
				L('SearchSub'),
				subtitle=L('SearchSub'),
				summary=L('SearchSum'),
				thumb=R(ICON),
				art=R(ART)
			)
		)
	)
		
	dir.Append(
		PrefsItem(
			title=L('Settings'),
			subtile=L('SettingsSub'), #Sub fails to display
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
		
	# History browsing
	if(feed.feed.has_key('link')):
		for link in feed.feed.links:
			if link.rel == 'prev-archive':
				dir.Append(
					Function(
						DirectoryItem(
							getMenu,
							L('Previous'),
							subtitle=L('PreviousSub') 
						), url=link.url
					)	
				)
			
	if feed['feed']['description'].find("Media RSS") == 0: # Video listing
		fixdict = {}
		
		if Prefs.Get('fixtitle'): #Ugly title hack
			simplefeed = feedparser.parse(url.split("/standard.mediarss")[0] + "/flv.rss")
			for fixentry in simplefeed.entries:
				if fixentry.has_key('link'):
					fixdict[fixentry.link] = fixentry.title
		
		for entry in feed.entries:
			try:
				title = ""
				description = ""
				thumbUrl = ""
				videoUrl = ""
				
				if type(entry.title).__name__ == 'unicode':
					title = entry.title
				else:
					Log("I'm a big bad bug!")
					Log(entry.get('title_detail', 'value'))
					
					if Prefs.Get('fixtitle'):
						if entry.link in fixdict:
							title = fixdict[entry.link]
				
				if title == "":
					title = type(entry.title).__name__ + repr(entry.title)
					
				try:
					description = entry.description
				except:
					description = ""
					Log("Empty description")
				
				if entry.has_key('media_thumbnail'):
					thumbUrl = authURL(entry.media_thumbnail[0]['url'])
				else:
					thumbUrl = ""
				
				prefbitrate = int(Prefs.Get('bitrate'))
				higherlink = ""				
				higherbitrate = 10000
				lowerlink = ""
				lowerbitrate = 0
				
				for content in entry.media_content:
					if content.has_key('bitrate'):
						bitrate = int(content['bitrate'])
						if bitrate == prefbitrate:
							videoUrl = authURL(content['url'])
							break
						elif bitrate < prefbitrate and bitrate > lowerbitrate:
							lowerbitrate = bitrate
							lowerlink = authURL(content['url'])
						elif bitrate > prefbitrate and bitrate < higherbitrate:
							higherbitrate = bitrate
							higherlink = authURL(content['url'])
				
				if videoUrl == "":
					if lowerbitrate != 0:
						videoUrl = lowerlink
					elif higherbitrate != 0:
						videoUrl = higherlink
						
				dir.Append(
					VideoItem(
						videoUrl,
						title,
						subtitle=formatdate(timegm(entry.updated_parsed), True), # Dates in localtime
						summary=description,
						thumb=thumbUrl
					)
				)
			except: # Missing info doesn't stop listing
				Log("-> missing information")
				raise
				
	else: # Directory
		for entry in feed.entries:
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
	
	return getMenu(sender=None, url=ROOT_URL+"search/title/"+search)
	
def authURL(url):
	url = "http://" + Prefs.Get('username') + ":" + Prefs.Get('password') + '@' + url.split("http://")[1]

	return url
