from globals import *
from webservice import PSVueWebService
from guideservice import BuildGuide

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
                    if image['width'] == 600 or image['width'] == 440:
                        logo = image['src']
                        logo = logo.encode('utf-8')
                        break
            url = 'http://127.0.0.1:' + ADDON.getSetting(id='port') + '/psvue?params=' + urllib.quote(CHANNEL_URL + '/' + channel_id)
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


def check_files():
    build_playlist()
    # build_epg()


class MainService:
    monitor = None
    last_update = None

    def __init__(self):
        self.monitor = xbmc.Monitor()

        xbmc.log('Calling PSVueWebService to start....')
        self.psvuewebservice = PSVueWebService()
        self.psvuewebservice.start()

        xbmc.log('Calling BuildGuide to start....')
        self.guideservice = BuildGuide()
        self.guideservice.start()

        self.last_update = datetime.now()
        check_files()

        xbmc.log("PS Vue EPG Update Check. Last Update: " + self.last_update.strftime('%m/%d/%Y %H:%M:%S'),
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

            xbmc.log("PS Vue EPG Update Check. Last Update: " + self.last_update.strftime('%m/%d/%Y %H:%M:%S'),
                     level=xbmc.LOGNOTICE)

        self.close()

    def close(self):
        self.psvuewebservice.stop()
        self.guideservice.stop()
        del self.monitor