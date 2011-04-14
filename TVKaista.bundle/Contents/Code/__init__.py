import feedparser
from email.utils import formatdate
from calendar import timegm

VIDEO_PREFIX = "/video/tvkaista"
ROOT_URL = "http://www.tvkaista.fi/feedbeta/"

NAME = L('Title')
ART  = 'art-default.jpg'
ICON = 'icon-default.png'

def Start():
	Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('VideoTitle'), ICON, ART)
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

	MediaContainer.art = R(ART)
	MediaContainer.title1 = NAME
	MediaContainer.viewGroup = "InfoList"
	DirectoryItem.thumb = R(ICON)
	VideoItem.thumb = R(ICON)

	HTTP.CacheTime = 60
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.16) Gecko/20110319 Firefox/3.6.16"


def MainMenu():
	dir = MediaContainer()
	dir.Append(Function(DirectoryItem(GetMenu, L('ChannelsTitle'), subtitle=L('ChannelsSub'), summary=L('ChannelsSum')), url=ROOT_URL+"channels/"))
	dir.Append(Function(DirectoryItem(GetMenu, L('SeasonsTitle'), subtitle=L('SeasonsSub'), summary=L('SeasonsSum')), url=ROOT_URL+"seasonpasses/"))
	dir.Append(Function(DirectoryItem(GetMenu, L('PlaylistTitle'), subtitle=L('PlaylistSub'), summary=L('PlaylistSum')), url=ROOT_URL+"playlist/"))
	dir.Append(Function(DirectoryItem(GetMenu, L('PopularTitle'), subtitle=L('PopularSub'), summary=L('PopularSum')), url=ROOT_URL+"programs/popular/"))
	dir.Append(Function(DirectoryItem(GetMenu, L('MoviesTitle'), subtitle=L('MoviesSub'), summary=L('MoviesSum')), url=ROOT_URL+"search/title/elokuva"))
	dir.Append(Function(InputDirectoryItem(SearchMenu, L('SearchTitle'), L('SearchSub'), subtitle=L('SearchSub'), summary=L('SearchSum'), thumb=R('icon-search.png'))))
	dir.Append(PrefsItem(title=L('Settings'), subtitle=L('SettingsSub'), summary=L('SettingsSum'), thumb=R('icon-prefs.png')))
	return dir


# Directory listing
def GetMenu(sender, url):
	dir = MediaContainer()

	if not Prefs['username'] and not Prefs['password']:
		return MessageContainer(L('Login'), L('EnterLogin'))

	url = AuthURL(url) # Add authentication to url
	feed = feedparser.parse(url)

	# History browsing
	if feed.feed.has_key('link'):
		for link in feed.feed.links:
			if link.rel == 'prev-archive':
				dir.Append(Function(DirectoryItem(GetMenu, L('Previous'), subtitle=L('PreviousSub')), url=link.url))

	if feed['feed']['description'].find("Media RSS") == 0: # Video listing
		fixdict = {}

		#Ugly title hack
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

				if entry.link in fixdict:
					title = fixdict[entry.link]
				else:
					title = "Unknown"
				
				try:
					description = entry.description
				except:
					description = ""

				if entry.has_key('media_thumbnail'):
					thumbUrl = AuthURL(entry.media_thumbnail[0]['url'])

				prefbitrate = int(Prefs['bitrate'])
				higherlink = ""				
				higherbitrate = 10000
				lowerlink = ""
				lowerbitrate = 0

				for content in entry.media_content:
					if content.has_key('bitrate'):
						bitrate = int(content['bitrate'])
						if bitrate == prefbitrate:
							videoUrl = AuthURL(content['url'])
							break
						elif bitrate < prefbitrate and bitrate > lowerbitrate:
							lowerbitrate = bitrate
							lowerlink = AuthURL(content['url'])
						elif bitrate > prefbitrate and bitrate < higherbitrate:
							higherbitrate = bitrate
							higherlink = AuthURL(content['url'])

				if videoUrl == "":
					if lowerbitrate != 0:
						videoUrl = lowerlink
					elif higherbitrate != 0:
						videoUrl = higherlink
				
				#dir.Append(VideoItem(videoUrl, title, subtitle=formatdate(timegm(entry.updated_parsed), True), summary=description, thumb=Function(GetThumb, url=thumbUrl))) # Dates in localtime
				dir.Append(VideoItem(videoUrl, title, subtitle=formatdate(timegm(entry.updated_parsed), True), summary=description, thumb=thumbUrl)) # Dates in localtime
			except: # Missing info doesn't stop listing
				Log("-> missing information")

	else: # Directory
		for entry in feed.entries:
			dir.Append(Function(DirectoryItem(GetMenu, entry.title, subtitle=entry.description), url=entry.link))

	if len(dir) == 0:
		return MessageContainer(L('Empty'), L('EmptyContainer'))
	else:
		return dir

def SearchMenu(sender,query=None):
	search = query.replace (' ', '+')
	return GetMenu(sender=None, url=ROOT_URL+"search/title/"+search)

def AuthURL(url):
	url = "http://" + Prefs['username'] + ":" + Prefs['password'] + '@' + url.split("http://")[1]
	return url

def GetThumb(url):
	try:
		data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
		return DataObject(data, 'image/jpeg')
	except:
		return Redirect(R(ICON))
