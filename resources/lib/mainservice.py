from webservice import PSVueWebService
import subprocess
import sys
import xbmcvfs
import time
import cookielib
import os, re
import requests, urllib
from datetime import datetime, timedelta
import xbmc, xbmcplugin, xbmcgui, xbmcaddon

ADDON = xbmcaddon.Addon()
PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
CHANNEL_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/channel'
EPG_URL = 'https://epg-service.totsuko.tv/epg_service_sony/service/v2'
SHOW_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/airing/'
VERIFY = False
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

if not xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
    dialog = xbmcgui.Dialog()
    dialog.notification('PS Vue EPG', 'Please enable PVR IPTV Simple Client', xbmcgui.NOTIFICATION_INFO, 5000, False)
    sys.exit()

IPTV_SIMPLE_ADDON = xbmcaddon.Addon('pvr.iptvsimple')


def build_playlist():
    json_source = get_json(EPG_URL + '/browse/items/channels/filter/all/sort/channeltype/offset/0/size/500')
    m3u_file = open(os.path.join(ADDON_PATH_PROFILE, "playlist.m3u"), "w")
    m3u_file.write("#EXTM3U")
    m3u_file.write("\n")

    channel_ids = []
    channel_names_str = ''
    for channel in json_source['body']['items']:
        title = channel['title']
        if channel['channel_type'] == 'linear':
            title = title.encode('utf-8')
            channel_id = str(channel['id'])
            channel_ids.append(channel_id)
            logo = None
            for image in channel['urls']:
                if 'width' in image:
                    xbmc.log(str(image['width']))
                    if image['width'] == 600 or image['width'] == 440:
                        logo = image['src']
                        logo = logo.encode('utf-8')
                        break
            url = 'http://127.0.0.1:54321/psvue?params=' + urllib.quote(CHANNEL_URL + '/' + channel_id) + '.m3u8'
            # url += '|User-Agent=' + urllib.quote(UA_ANDROID_TV)
            # 'Access-Control-Allow-Origin': 'http://totsuko.tv',
            url += '|User-Agent=' + 'Adobe Primetime/1.4 Dalvik/2.1.0 (Linux; U; Android 6.0.1 Build/MOB31H)'

            m3u_file.write("\n")
            channel_info = '#EXTINF:-1 tvg-id="' + channel_id + '" tvg-name="' + title + '"'

            if logo is not None: channel_info += ' tvg-logo="' + logo + '"'
            channel_info += ' group_title="PS Vue",' + title
            m3u_file.write(channel_info + "\n")
            m3u_file.write(url + "\n")

            channel_names_str += '<channel id="' + channel_id + '">\n'
            channel_names_str += '    <display-name lang="en">' + title + '</display-name>\n'
            channel_names_str += '</channel>\n'

    m3u_file.close()

    channel_ids_str = ",".join(channel_ids)
    PS_VUE_ADDON.setSetting(id='channelIDs', value=channel_ids_str)
    PS_VUE_ADDON.setSetting(id='channelNamesXML', value=channel_names_str)

    check_iptv_setting('epgTSOverride', 'true')
    check_iptv_setting('m3uPathType', '0')
    check_iptv_setting('m3uPath', os.path.join(ADDON_PATH_PROFILE, "playlist.m3u"))
    check_iptv_setting('logoFromEpg', '1')
    check_iptv_setting('logoPathType', '1')


def build_epg():
    channel_ids = PS_VUE_ADDON.getSetting('channelIDs').split(',')
    channel_names_xml = PS_VUE_ADDON.getSetting('channelNamesXML')
    xmltv_file = open(os.path.join(ADDON_PATH_PROFILE, "epg.xml"), "w")
    xmltv_file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    xmltv_file.write("<tv>\n")
    xmltv_file.write(channel_names_xml)

    xbmc.log("-----------------------------------------------------------------------------------------------------")
    xbmc.log(str(channel_ids))
    xbmc.log(channel_names_xml)
    xbmc.log("-----------------------------------------------------------------------------------------------------")

    progress = xbmcgui.DialogProgressBG()
    progress.create('PS Vue EPG')
    progress.update(0, 'Retrieving Programming Information...')

    i = 1
    for channel in channel_ids:
        percent = int((float(i) / len(channel_ids)) * 100)
        message = "Loading channel " + str(i) + ' of ' + str(len(channel_ids))
        progress.update(percent, message)
        # build_epg_channel(xmltv_file, channel)
        if xbmc.Monitor().abortRequested(): break
        i += 1

    xmltv_file.write('</tv>\n')
    xmltv_file.close()
    progress.update(100, 'Done!')
    progress.close()

    check_iptv_setting('epgPathType', '0')
    check_iptv_setting('epgPath', os.path.join(ADDON_PATH_PROFILE, "epg.xml"))


def build_epg_channel(xmltv_file, channel_id):
    json_source = get_json(EPG_URL + '/timeline/live/' + channel_id + '/watch_history_size/0/coming_up_size/50')
    for strand in json_source['body']['strands']:
        if xbmc.Monitor().abortRequested(): break
        if strand['id'] == 'now_playing' or strand['id'] == 'coming_up':
            for program in strand['programs']:
                icon = ""
                for image in program['urls']:
                    if 'width' in image:
                        if image['width'] == 600 or image['width'] == 440:
                            icon = image['src']
                            break

                title = program['title']
                title = title.encode('utf-8')
                xbmc.log(title)
                sub_title = ''

                if 'title_sub' in program:
                    sub_title = program['title_sub']
                    sub_title = sub_title.encode('utf-8')
                desc = ''

                if 'synopsis' in program:
                    desc = program['synopsis']
                    desc = desc.encode('utf-8')
                # start_time = datetime.strptime(program['airing_date'], DATE_FORMAT)
                start_time = string_to_date(program['airing_date'], DATE_FORMAT)
                start_time = start_time.strftime("%Y%m%d%H%M%S")
                # stop_time = datetime.strptime(program['expiration_date'], DATE_FORMAT)
                stop_time = string_to_date(program['expiration_date'], DATE_FORMAT)
                stop_time = stop_time.strftime("%Y%m%d%H%M%S")

                xmltv_file.write(
                    '<programme start="' + start_time + '" stop="' + stop_time + '"  channel="' + channel_id + '">\n')
                xmltv_file.write('    <title lang="en">' + title + '</title>\n')
                xmltv_file.write('    <sub-title lang="en">' + sub_title + '</sub-title>\n')
                xmltv_file.write('    <desc lang="en">' + desc + '</desc>\n')
                for item in program['genres']:
                    genre = item['genre']
                    genre = genre.encode('utf-8')
                    xmltv_file.write('    <category lang="en">' + genre + '</category>\n')

                xmltv_file.write('    <icon src="' + icon + '"/>\n')
                xmltv_file.write('</programme>\n')


def airings():
    """
     POST https://epg-service.totsuko.tv/epg_service_sony/service/v2/airings HTTP/1.1
     Host: epg-service.totsuko.tv
     Connection: keep-alive
     Content-Length: 157
     Accept: */*
     reqPayload:
     User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36
     Origin: https://vue.playstation.com
     Content-Type: application/json
     Referer: https://vue.playstation.com/watch/guide
     Accept-Encoding: gzip, deflate, br
     Accept-Language: en-US,en;q=0.9

     {"start":"2018-03-09T16:00:00.000Z","end":"2018-03-10T22:03:00.000Z","channel_ids":[25436,25076,25093,856,15478,25039,4579,25159,2754,25346,100,25347,25348]}
     {"start":"2018-03-17T062414.000Z","end":"2018-03-20T122414.000Z","channel_ids":[25436,25182,25109,25077,25389,25464,7177,13461,25017,25101,25113,25138,25164,25069,4336,7320,13468,3714,25565,7830,25076,25095,25209,25023,25272,12865,25093,441,25210,856,25281,15478,16286,3545,25475,5414,12378,12822,13239,25301,7483,25039,4579,25263,16256,25097,13435,25474,5212,25747,25736,25746,25075,25167,25180,25091,25228,24541,25486,10283,15801,7427,25451,25159,24988,25183,25535,25098,25099,25261,2754,25283,25257,25499,25179,13460,5375,16527,2755,24998,25081,25030,10510,15834,25078,12092,25181]}
     :return:

    channel_ids = PS_VUE_ADDON.getSetting('channelIDs')
    url = 'https://epg-service.totsuko.tv/epg_service_sony/service/v2/airings'
    headers = {
        'Accept': '*/*',
        'reqPayload': PS_VUE_ADDON.getSetting(id='EPGreqPayload'),
        'User-Agent': UA_ANDROID_TV,
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Requested-With': 'com.snei.vue.android',
        'Connection': 'keep-alive',
        'Origin': 'https://vue.playstation.com',
        'Content-Type': 'application/json',
        'Referer': 'https://vue.playstation.com/watch/guide'
    }

    utc_start = datetime.utcnow() - timedelta(hours=2)
    utc_end = datetime.utcnow() + timedelta(hours=6)
    payload = '{"start":"' + utc_start.strftime(DATE_FORMAT) + '","end":"' + utc_end.strftime(DATE_FORMAT) + '","channel_ids":[' + channel_ids + ']}'

    r = requests.post(url, headers=headers, cookies=load_cookies(), data=payload, verify=VERIFY)

    i = 1

    for program in r.json()['body']['airings']:
        percent = int((float(i) / len(r.json()['body']['airings'])) * 100)
        message = "Loading channel " + str(i) + ' of ' + str(len(r.json()['body']['airings']))
        progress.update(percent, message)
        build_epg_channel(xmltv_file, program)
        i += 1

    channel_id = str(program['channel_id'])
    title = program['title']
    title = title.encode('utf-8')
    sub_title = ''
    if 'title_sub' in program:
        sub_title = program['title_sub']
        sub_title = sub_title.encode('utf-8')
    desc = ''

    if 'synopsis' in program:
        desc = program['synopsis']
        desc = desc.encode('utf-8')
    start_time = datetime.strptime(program['start'], DATE_FORMAT)
    start_time = start_time.strftime("%Y%m%d%H%M%S")
    stop_time = datetime.strptime(program['end'], DATE_FORMAT)
    stop_time = stop_time.strftime("%Y%m%d%H%M%S")

    xmltv_file.write('<programme start="' + start_time + '" stop="' + stop_time + '" channel="' + channel_id + '">\n')
    xmltv_file.write('    <title lang="en">' + title + '</title>\n')
    xmltv_file.write('    <sub-title lang="en">' + sub_title + '</sub-title>\n')
    xmltv_file.write('    <desc lang="en">' + desc + '</desc>\n')
    if 'genres' in program:
        for item in program['genres']:
            genre = item['genre']
            genre = genre.encode('utf-8')
            xmltv_file.write('    <category lang="en">' + genre + '</category>\n')
    xmltv_file.write('</programme>\n')
    """


def get_json(url):
    headers = {
        'Accept': '*/*',
        'reqPayload': PS_VUE_ADDON.getSetting(id='EPGreqPayload'),
        'User-Agent': UA_ANDROID_TV,
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Requested-With': 'com.snei.vue.android',
        'Connection': 'keep-alive'
    }

    r = requests.get(url, headers=headers, cookies=load_cookies(), verify=VERIFY)

    if r.status_code != 200:
        dialog = xbmcgui.Dialog()
        msg = 'The request could not be completed.'
        try:
            json_source = r.json()
            msg = json_source['header']['error']['message']
        except:
            pass
        dialog.notification('Error ' + str(r.status_code), msg, xbmcgui.NOTIFICATION_INFO, 9000)
        sys.exit()
    return r.json()


def load_cookies():
    cookie_file = os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp')
    cj = cookielib.LWPCookieJar()
    try:
        cj.load(cookie_file, ignore_discard=True)
    except:
        pass
    return cj


def find(source, start_str, end_str):
    start = source.find(start_str)
    end = source.find(end_str, start + len(start_str))
    if start != -1:
        return source[start + len(start_str):end]
    else:
        return ''


def string_to_date(string, date_format):
    try:
        date = datetime.strptime(str(string), date_format)
    except TypeError:
        date = datetime(*(time.strptime(str(string), date_format)[0:6]))
    return date


def check_iptv_setting(id, value):
    if IPTV_SIMPLE_ADDON.getSetting(id) != value:
        IPTV_SIMPLE_ADDON.setSetting(id=id, value=value)


def check_files():
    build_playlist()
    build_epg()


class MainService:
    monitor = None
    last_update = None

    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.psvuewebservice = PSVueWebService()
        self.psvuewebservice.start()
        last_update = datetime.now()
        check_files()
        xbmc.log("PS Vue EPG Update Check. Last Update: " + last_update.strftime('%m/%d/%Y %H:%M:%S'),
                 level=xbmc.LOGNOTICE)
        self.main_loop()

    def main_loop(self):
        while not self.monitor.abortRequested():
            # Sleep/wait for abort for 10 minutes
            if self.monitor.waitForAbort(600):
                # Abort was requested while waiting. We should exit
                break
            if self.last_update < datetime.now() - timedelta(hours=1):
                check_files()
                self.last_update = datetime.now()

            xbmc.log("PS Vue EPG Update Check. Last Update: " + last_update.strftime('%m/%d/%Y %H:%M:%S'),
                     level=xbmc.LOGNOTICE)

        self.close()

    def close(self):
        self.psvuewebservice.stop()
        del self.monitor