from xml.etree.ElementTree import XML
from time import strptime, localtime, mktime
from calendar import timegm

import urllib2
import sys
import re
import base64

# For information, not used directly
mrss_ns = { 'dc': "http://purl.org/dc/elements/1.1/",
            'fh': "http://purl.org/syndication/history/1.0",
            'media': "http://search.yahoo.com/mrss/",
            'atom': "http://www.w3.org/2005/Atom" }

day_name = [ 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 
        'Saturday', 'Sunday' ]
short_day_name = [ 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su' ]

VIDEO_PREFIX = "/video/tvkaista2"
ROOT_URL = "http://www.tvkaista.fi/feed/"

NAME = L('Title')
ART  = 'art-default.jpg'
ICON = 'icon-default.png'


def safe_get_text(item, default=None):
    try:
        value = item.text
    except:
        value = default

    return value


def safe_get_attrib(d, key, default=None):
    if key in d:
        return d[key]

    return default


def read_content(url):
    username = Prefs['username']
    password = Prefs['password']
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string

    req = urllib2.Request(url)
    req.add_header("Authorization", authheader)
    try:
        handle = urllib2.urlopen(req)
    except IOError, e:
        # here we shouldn't fail if the username/password is right
        Log("It looks like the username or password is wrong.")
	return None

    return handle.read()


def Channels(content):
    result = []
    feed = XML(content)
    for item in feed.findall('channel/item'):
        title = safe_get_text(item.find('title'), "UNKNOWN")
        desc = safe_get_text(item.find('description'), "")
        url = safe_get_text(item.find('link'))
        if url:
            chid = url.split('/')[-1]
        else:
            chid = None
        
        result.append((title, desc, url, chid))
        
    return result

        
def Videos(content, bitrate=8000):
    def matching_video(videos, bitrate):
        current = { }
        
        for video in videos:
            video_bitrate = int(safe_get_attrib(video.attrib, 'bitrate', 0))
            current_bitrate = int(safe_get_attrib(current, 'bitrate', 0))
            if (video_bitrate <= bitrate) and \
               (video_bitrate > current_bitrate):
                current = video.attrib 

        return (safe_get_attrib(current, 'url'), 
                safe_get_attrib(current, 'duration', ""))
        
    def best_thumb(thumbs):
        current = { }
        
        for thumb in thumbs:
            height = int(safe_get_attrib(thumb.attrib, 'height', 0))
            current_height = int(safe_get_attrib(current, 'height', 0))
            if height >= current_height:
                current = thumb.attrib
                
        return safe_get_attrib(current, 'url', R(ICON))
    
    result = []
    feed = XML(content)
    for item in feed.findall('channel/item'):
        pubdate = safe_get_text(item.find('pubDate'))
        source = safe_get_text(item.find('source'))
        if pubdate:
            try:
                pubdate = localtime(timegm(strptime(pubdate, 
                                                    '%a, %d %b %Y %H:%M:%S +0000')))
            except:
                pubdate = None

        url, duration = matching_video(item.findall('{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}content'), bitrate)
        thumb = best_thumb(item.findall('{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}thumbnail'))
        title = safe_get_text(item.find('{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}title'), 
                              "UNKNOWN")
        desc = safe_get_text(item.find('{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}description'), 
                             title)

        if pubdate:
            title = "%02d:%02d %s" % (pubdate.tm_hour, pubdate.tm_min, title)
        result.append((title, desc, pubdate, AuthUrl(url), 
	               thumb, duration, source))
    return result


def AuthUrl(url):
    user = Prefs['username']
    pswd = Prefs['password']
    try:
        ret_url = "http://%s:%s@%s" % (user, pswd, url.split("http://")[1])
    except:
        ret_url = None
    return ret_url
        

def Start():
    Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, 
                            L('VideoTitle'), ICON, ART)
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", 
                        mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    MediaContainer.viewGroup = "InfoList"
    DirectoryItem.thumb = R(ICON)
    VideoItem.thumb = R(ICON)


def GetThumb(url):
    data = read_content(url)
    return DataObject(data, 'image/jpeg')


def GetListing(sender, url, reverse=False, add_date=False):
    bitrate = int(Prefs['bitrate'])

    data = read_content(url)
    video_list = Videos(data, bitrate)

    if not video_list:
        return MessageContainer(L('Empty'), L('EmptyContainer'))

    if reverse:
        video_list.reverse()

    dir = MediaContainer()
    for title, desc, pubdate, url, thumb, duration, source in video_list:
        if add_date:
	    title = title + " (%s %02d.%02d" % \
                            (short_day_name[pubdate.tm_wday],
                             pubdate.tm_mday, pubdate.tm_mon)
            if source:
		title = title + ", " + source
            title = title + ")"
        if not url:
            title = "[%s]" % (title)
        dir.Append(VideoItem(url, 
                             title, 
                             summary=desc,
                             thumb=Function(GetThumb, url=thumb)))
    return dir
        

def GetMenu(sender, url, reverse=False, add_date=False):
    data = read_content(url)
    channel_list = Channels(data)
    if not channel_list:
        return MessageContainer(L('Empty'), L('EmptyContainer'))
        
    dir = MediaContainer()
    for title, desc, url, chid in channel_list:
        dir.Append(Function(DirectoryItem(GetListing, 
                                          title, 
                                          subtitle=desc), 
                            url=url,
			    reverse=reverse,
			    add_date=add_date))    
    return dir


def GetDayMenu(sender, url, chid, title):
    def past_days(n):
	now = mktime(localtime())
	SECONDS_IN_DAY=24*60*60
        lst = []
	for i in range(n):
	   now = now - SECONDS_IN_DAY
	   d = localtime(now)
	   lst.append((d.tm_year, d.tm_mon, d.tm_mday, d.tm_wday))

        return lst

    dir = MediaContainer()
    dir.Append(Function(DirectoryItem(GetListing, L('TodayTitle'),
                                      subtitle=title,
                                      summary=L('TodaySum')),
                        url=url, 
                        reverse=True))
    for year, month, day, weekday in past_days(28):
        name = "%02d.%02d %s" % (day, month, day_name[weekday])
        desc = "Recordings for %s %02d.%02d.%04d" % (day_name[weekday],
                                                     day, month, year)
        url = ROOT_URL + "archives/%04d/%02d/%02d/channels/%s" % \
                         (year, month, day, chid)
	dir.Append(Function(DirectoryItem(GetListing, name,
                                          subtitle=title,
                                          summary=desc),
                            url=url))

    return dir


def GetChannelMenu(sender, url):
    data = read_content(url)
    channel_list = Channels(data)
    if not channel_list:
        return MessageContainer(L('Empty'), L('EmptyContainer'))

    dir = MediaContainer()
    for title, desc, url, chid in channel_list:
        subdir = dir.Append(Function(DirectoryItem(GetDayMenu, title,
						  subtitle=desc),
                                     url=url,
			             chid=chid,
                                     title=title))
    return dir

def SearchMenu(sender, query):
    search = query.replace(' ','+')
    return GetListing(sender=None, url=ROOT_URL+"search/title/"+search,
                      reverse=True, add_date=True)


def MainMenu():
    
    dir = MediaContainer()
        
    dir.Append(Function(DirectoryItem(GetChannelMenu, L('ChannelsTitle'), 
                                      subtitle=L('ChannelsSub'), 
                                      summary=L('ChannelsSum')), 
                        url=ROOT_URL+"channels/"))
    dir.Append(Function(DirectoryItem(GetListing, L('MoviesTitle'), 
                                      subtitle=L('MoviesSub'), 
                                      summary=L('MoviesSum')), 
                        url=ROOT_URL+"search/title/elokuva",
			add_date=True))
    dir.Append(Function(DirectoryItem(GetMenu, L('SeasonsTitle'), 
                                      subtitle=L('SeasonsSub'), 
                                      summary=L('SeasonsSum')), 
                        url=ROOT_URL+"seasonpasses/",
			add_date=True))
    dir.Append(Function(InputDirectoryItem(SearchMenu, L('SearchTitle'),
                                           L('SearchSub'),
                                           subtitle=L('SearchSub'),
                                           summary=L('SearchSum'),
                                           thumb=R('icon-search.png'))))
    dir.Append(Function(DirectoryItem(GetListing, L('LatestTitle'), 
                                      subtitle=L('LatestSub'), 
                                      summary=L('LatestSum')), 
                        url=ROOT_URL+"seasonpasses/*/",
			add_date=True,
                        reverse=True))
    dir.Append(PrefsItem(title=L('Settings'), 
                         subtitle=L('SettingsSub'), 
                         summary=L('SettingsSum'), 
                         thumb=R('icon-prefs.png')))
    return dir

