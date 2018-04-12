import cookielib
from datetime import datetime, timedelta
import os
import threading
import time
import requests
import sys
import urllib
import xbmc, xbmcgui, xbmcaddon


ADDON = xbmcaddon.Addon()
PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
CHANNEL_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/channel'
EPG_URL = 'https://epg-service.totsuko.tv/epg_service_sony/service/v2'
SHOW_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/airing/'
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
IPTV_SIMPLE_ADDON = xbmcaddon.Addon('pvr.iptvsimple')
VERBOSE = True
VERIFY = False
