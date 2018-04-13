import glob
import math
import xbmcvfs
from globals import *


def sleep(time, units):
    if units == 'm':
        time /= 1000
    elif units == 'M':
        time *= 60

    xbmc.Monitor().waitForAbort(time)


def find(source, start_str, end_str):
    start = source.find(start_str)
    end = source.find(end_str, start + len(start_str))
    if start != -1:
        return source[start + len(start_str):end]
    else:
        return ''


def guide_runner(guide_path, guide_date, guide_timestamp, guide_sequence):
    if VERBOSE:
        xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + ' Started - > Guide Path: ' + str(guide_path) +
                 ' | Guide Timestamp: ' + guide_timestamp + ' | ' + guide_sequence)

    if not os.path.isdir(guide_path):
        xbmcvfs.mkdir(guide_path)

    guide_file = 'epg_' + guide_timestamp + '_' + guide_sequence + '.xml'

    if not xbmcvfs.exists(os.path.join(guide_path, guide_file)):
        if VERBOSE:
            xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + 'Creating guide file: ' + guide_file)
        file = open(os.path.join(guide_path, guide_file), 'w')
        build_guide_file(file, guide_sequence, guide_date)
        file.close()

        if VERBOSE:
            xbmc.log('BuildGuide Thread ' + guide_sequence + ': Built guide file -> ' + guide_file)
    else:
        if VERBOSE:
            xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + 'File ' + guide_file + ' already exists, exiting.')

    #now = datetime.now()
    #today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)
    today_timestamp = datetime.now().strftime('%Y%m%d')

    xbmc.log('================================Checking If Current Guide file================================')
    xbmc.log('Guide Timestamp | Today Timestamp: ' + guide_timestamp + ' | ' + today_timestamp + ' -> ' + str(
        guide_timestamp == today_timestamp))
    xbmc.log('Hour/Ceiling | Guide Sequence: ' + str(now.hour) + '/' + str(
        math.ceil(now.hour / 6.0) - 4) + ' | ' + guide_sequence + ' -> ' + str(
        math.ceil(now.hour / 6.0) == int(guide_sequence)))
    xbmc.log('File ' + guide_file + ' Exists: ' + str(os.path.exists(os.path.join(guide_path, guide_file))))



    # if guide_timestamp == today_timestamp and math.ceil(now.hour / 6.0) == int(guide_sequence) \
    #         and os.path.exists(guide_path + guide_file):
    # master_file = guide_path + 'epg_master.xml'
    # copyfile(guide_path + guide_file, master_file)
    # check_iptv_setting('epgPathType', '0')
    # check_iptv_setting('epgPath', master_file)

    # if VERBOSE:
    #    xbmc.log('BuildGuide Thread ' + guide_sequence + ': Applied guide file -> ' + guide_file)


def build_guide_file(xmltv_file, guide_sequence, guide_date):
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

    guide_midnight = guide_date + timedelta(hours=(-1 * guide_date.hour),
                                                     minutes=(-1 * guide_date.minute),
                                                     seconds=(-1 * guide_date.second))
    guide_start = guide_midnight + timedelta(hours=((int(guide_sequence) - 1) * 6))
    guide_end = guide_midnight + timedelta(hours=(int(guide_sequence) * 6))
    payload = '{"start":"' + guide_start.strftime(DATE_FORMAT) + '","end":"' + guide_end.strftime(
        DATE_FORMAT) + '","channel_ids":[' + channel_ids + ']}'
    xbmc.log('BuildGuide Payload (Thread ' + guide_sequence + '): ' + str(guide_start) + ' | ' + str(guide_end))
    xbmc.log(
        'BuildGuide TimeDelta (Thread ' + guide_sequence + '): ' + str(((int(guide_sequence) - 1) * 6)) + ' | ' + str(
            (int(guide_sequence) * 6)))

    r = requests.post(url, headers=headers, cookies=load_cookies(), data=payload, verify=VERIFY)

    for program in r.json()['body']['airings']:
        build_epg_channel(xmltv_file, program)


def build_epg_channel(xmltv_file, program):
    channel_id = str(program['channel_id'])
    title = program['title'].replace('&', 'and')
    title = title.encode('utf-8')
    sub_title = ''
    if 'title_sub' in program:
        sub_title = program['title_sub'].replace('&', 'and')
        sub_title = sub_title.encode('utf-8')
    desc = ''

    if 'synopsis' in program:
        desc = program['synopsis']
        desc = desc.encode('utf-8')

    start_time = string_to_date(program['start'], DATE_FORMAT)
    start_time = start_time.strftime("%Y%m%d%H%M%S")
    stop_time = string_to_date(program['end'], DATE_FORMAT)
    stop_time = stop_time.strftime("%Y%m%d%H%M%S")

    xmltv_file.write('<programme start="' + start_time + '" stop="' + stop_time + '" channel="' + channel_id + '">\n')
    xmltv_file.write('    <title lang="en">' + title.replace('&', 'and') + '</title>\n')
    xmltv_file.write('    <sub-title lang="en">' + sub_title.replace('&', 'and') + '</sub-title>\n')
    xmltv_file.write('    <desc lang="en">' + desc.replace('&', 'and') + '</desc>\n')
    if 'genres' in program:
        for item in program['genres']:
            genre = item['genre']
            genre = genre.encode('utf-8')
            xmltv_file.write('    <category lang="en">' + genre + '</category>\n')
    xmltv_file.write('</programme>\n')


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
        except Exception as e:
            if VERBOSE:
                xbmc.log('BuildGuide: Exception thrown in get_json -> ' + str(e))
            pass
        dialog.notification('Error ' + str(r.status_code), msg, xbmcgui.NOTIFICATION_INFO, 9000)
        sys.exit()
    return r.json()


def string_to_date(string, date_format):
    try:
        date = datetime.strptime(str(string), date_format)
    except TypeError:
        date = datetime(*(time.strptime(str(string), date_format)[0:6]))
    return date


def load_cookies():
    cookie_file = os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp')
    cj = cookielib.LWPCookieJar()
    try:
        cj.load(cookie_file, ignore_discard=True)
    except:
        pass
    return cj


def check_iptv_setting(id, value):
    if IPTV_SIMPLE_ADDON.getSetting(id) != value:
        IPTV_SIMPLE_ADDON.setSetting(id=id, value=value)

    xbmc.log('BuildGuide: PVR guide updated, toggling IPTV restart')
    xbmc.executebuiltin('StartPVRManager')


def erase_stale_files(guide_path, today_timestamp):
    if VERBOSE:
        xbmc.log('BuildGuide: Inside ' + guide_path + '\nwill delete anything older than ' + today_timestamp)

    files = glob.glob(os.path.join(guide_path, '*.xml'))

    if files:
        for file_path in files:
            try:
                file = file_path.rsplit('\\', 1)[1]
                file_timestamp = find(file, 'epg_', '_')
                if file_timestamp < today_timestamp:
                    if VERBOSE:
                        xbmc.log('BuildGuide: ' + file + ' is older than ' + today_timestamp + ', will delete...')
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        if VERBOSE:
                            xbmc.log('BuildGuide: Failed to delete old guide file -> ' + file_path + '\nException:' + e)
                else:
                    if VERBOSE:
                        xbmc.log('BuildGuide: ' + file + ' is current, ignoring.')

            except Exception as e:
                if VERBOSE:
                    xbmc.log('BuildGuide: failed to retrieve file for checking: ' + str(e))

    else:
        if VERBOSE:
            xbmc.log('BuildGuide: Directory is empty, nothing to delete')
    return


def build_master_file(guide_path):
    xbmc.log('BuildGuide: Building master file...')

    #now = datetime.now()
    #today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)
    today_timestamp = datetime.now().strftime('%Y%m%d')

    channel_names_xml = PS_VUE_ADDON.getSetting('channelNamesXML')
    temp_file = os.path.join(guide_path, 'epg_temp_master.xml')
    master_file = open(temp_file, 'w')

    master_file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    master_file.write("<tv>\n")
    master_file.write(channel_names_xml)

    files = sorted(glob.glob(os.path.join(guide_path, '*.xml')))
    xbmc.log("BuildGuide: Files list: " + str(files))
    if files:
        for file_path in files:
            try:
                #file_name = file_path.rsplit('\\', 1)[1]
                #if 'master' not in file_name:
                if 'master.xml' not in file_name
                    file = open(file_path)
                    for line in file:
                        line = str(line)
                        master_file.write(line)
                else:
                    xbmc.log('BuildGuide: Skipping master file -> ' + file_name)

            except Exception as e:
                if VERBOSE:
                    xbmc.log('BuildGuide: failed to retrieve file for checking: ' + str(e))

        master_file.write('</tv>')
        master_file.close()
        xbmcvfs.copy(temp_file, os.path.join(guide_path, 'epg_' + today_timestamp + '_master.xml'))
        xbmcvfs.copy(temp_file, os.path.join(ADDON_PATH_PROFILE, 'epg.xml'))
        #xbmcvfs.delete(temp_file)
        xbmc.log('BuildGuide: Master file built.')

        check_iptv_setting('epgPath', os.path.join(ADDON_PATH_PROFILE, 'epg.xml'))
        xbmc.log('BuildGuide: PVR guide updated, toggling IPTV restart')
        xbmc.executebuiltin('StartPVRManager')


class BuildGuide(threading.Thread):
    guide_days = int(ADDON.getSetting('epg_days'))
    #guide_path = os.path.join(ADDON_PATH_PROFILE, "epg" + "\\")
    guide_path = os.path.join(ADDON_PATH_PROFILE, "epg")
    guide_thread_1 = None
    guide_thread_2 = None
    guide_thread_3 = None
    guide_thread_4 = None
    keep_running = True
    up_to_date = False
    monitor = xbmc.Monitor()

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        if VERBOSE:
            xbmc.log('BuildGuide: Thread starting....')

        #while self.keep_running:
        while not self.monitor.abortRequested():
            now = datetime.utcnow()

            #today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)
            today_timestamp = datetime.now().strftime('%Y%m%d')
            if not self.up_to_date:
                if VERBOSE:
                    xbmc.log('BuildGuide: Erasing stale files....')
                #erase_stale_files(self.guide_path, today_timestamp)
                erase_stale_files(self.guide_path, today_timestamp)

                if VERBOSE:
                    xbmc.log('BuildGuide: Looping through guide days....')
                for guide_day in range(0, self.guide_days):
                    guide_date = now + timedelta(days=guide_day)
                    guide_timestamp = str(guide_date.year) + str(guide_date.month).zfill(2) + str(guide_date.day).zfill(
                        2)

                    self.guide_thread_1 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(self.guide_path, guide_date,
                                                                               guide_timestamp,
                                                                               '1'))
                    self.guide_thread_2 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(self.guide_path, guide_date,
                                                                               guide_timestamp,
                                                                               '2'))
                    self.guide_thread_3 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(self.guide_path, guide_date,
                                                                               guide_timestamp,
                                                                               '3'))
                    self.guide_thread_4 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(self.guide_path, guide_date,
                                                                               guide_timestamp,
                                                                               '4'))

                    thread_alive = True
                    while thread_alive:
                        thread_alive = False
                        if self.guide_thread_1.isAlive() or self.guide_thread_2.isAlive() or self.guide_thread_3.isAlive() \
                                or self.guide_thread_4.isAlive():
                            thread_alive = True
                        if VERBOSE:
                            xbmc.log('BuildGuide: Active threads remain, waiting 5 seconds')

                if VERBOSE:
                    xbmc.log('BuildGuide: Guide up to date, going idle')

                self.up_to_date = True

                #now = datetime.now()
                #today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)
                if not xbmcvfs.exists(os.path.join(self.guide_path, 'epg_' + today_timestamp + '_master.xml')):
                    build_master_file(self.guide_path)

            #if now.minute == 0:
            if self.monitor.waitForAbort(600):
                break

            self.up_to_date = False

    def stop(self):
        if VERBOSE:
            xbmc.log('BuildGuide: Stop triggered....')

        self.keep_running = False
        self.join(0)