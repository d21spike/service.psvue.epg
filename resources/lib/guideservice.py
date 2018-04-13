import glob
import math
import sqlite3
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


def guide_runner(guide_date, guide_sequence, db_path):
    db_connection = sqlite3.connect(db_path)
    program_list = build_guide_file(guide_sequence, guide_date)

    db_connection.executemany('insert into epg (StartTime, EndTime, Channel, Title, SubTitle, Desc) values (?,?,?,?,?,?)', program_list)
    db_connection.commit()
    db_connection.close()


def build_guide_file(guide_sequence, guide_date):
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

    """
    guide_midnight = guide_date + timedelta(hours=(-1 * guide_date.hour),
                                                     minutes=(-1 * guide_date.minute),
                                                     seconds=(-1 * guide_date.second))
    """
    #guide_start = guide_midnight + timedelta(hours=(int(guide_sequence) * 6))
    #guide_end = guide_midnight + timedelta(hours=(int(guide_sequence) * 6))
    guide_start = datetime.utcnow()
    guide_end = datetime.utcnow() + timedelta(days=2)
    #guide_end = datetime.utcnow() + timedelta(days=int(ADDON.getSetting('epg_days')))

    payload = '{"start":"' + guide_start.strftime(DATE_FORMAT) + '","end":"' + guide_end.strftime(DATE_FORMAT) + '","channel_ids":[' + channel_ids + ']}'

    r = requests.post(url, headers=headers, cookies=load_cookies(), data=payload, verify=VERIFY)
    programs_list = []
    for program in r.json()['body']['airings']:
        programs_list.append(build_epg_channel(program))

    return programs_list


def build_epg_channel(program):
    channel_id = str(program['channel_id'])
    title = program['title']
    sub_title = ''
    if 'title_sub' in program:
        sub_title = sub_title
    desc = ''

    if 'synopsis' in program:
        desc = program['synopsis']
        desc = desc

    start_time = string_to_date(program['start'], DATE_FORMAT)
    start_time = start_time.strftime("%Y%m%d%H%M%S")
    stop_time = string_to_date(program['end'], DATE_FORMAT)
    stop_time = stop_time.strftime("%Y%m%d%H%M%S")

    return start_time, stop_time, channel_id, title, sub_title, desc


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


def build_master_file(db_path, guide_path):
    db_connection = sqlite3.connect(db_path)
    db_cursor = db_connection.cursor()
    xbmc.log('BuildGuide: Building master file...')

    now = (datetime.now().strftime('%Y%m%d%H%M%S'),)
    db_connection.execute('delete from epg where endtime < ?', now)
    db_connection.commit()

    channel_names_xml = PS_VUE_ADDON.getSetting('channelNamesXML')
    temp_file = os.path.join(guide_path, 'epg.xml')
    master_file = open(temp_file, 'w')

    master_file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    master_file.write("<tv>\n")
    master_file.write(channel_names_xml)

    db_cursor.execute("select * from epg")
    for row in db_cursor:
        start_time = str(row[0])
        stop_time = str(row[1])
        channel_id = str(row[2])
        title = row[3]
        sub_title = row[4]
        desc = row[5]
        line = ''
        line += '<programme start="' + start_time + '" stop="' + stop_time + '" channel="' + channel_id + '">\n'
        line += '    <title lang="en">' + title.encode('utf-8') + '</title>\n'
        line += '    <sub-title lang="en">' + sub_title.encode('utf-8') + '</sub-title>\n'
        line += '    <desc lang="en">' + desc.encode('utf-8') + '</desc>\n'
        line += '</programme>\n'
        master_file.write(line)

    master_file.write('</tv>')
    master_file.close()
    db_connection.close()
    #xbmcvfs.copy(temp_file, os.path.join(ADDON_PATH_PROFILE, 'epg.xml'))
    # xbmcvfs.delete(temp_file)
    xbmc.log('BuildGuide: Master file built.')

    check_iptv_setting('epgPath', os.path.join(ADDON_PATH_PROFILE, 'epg.xml'))
    xbmc.log('BuildGuide: PVR guide updated, toggling IPTV restart')
    xbmc.executebuiltin('StartPVRManager')


def init_db(db_path):
    if not xbmcvfs.exists(db_path):
        # Create db file if it doesn't exist
        open(db_path, 'a').close()

    db_connection = sqlite3.connect(db_path)

    sql = 'create table if not exists epg ('
    sql += 'StartTime integer,'
    sql += 'EndTime integer,'
    sql += 'Channel integer,'
    sql += 'Title text,'
    sql += 'SubTitle text,'
    sql += 'Desc text'
    sql += ')'

    db_connection.execute(sql)
    db_connection.commit()
    db_connection.close()


class BuildGuide(threading.Thread):
    guide_days = int(ADDON.getSetting('epg_days'))
    guide_path = os.path.join(ADDON_PATH_PROFILE)
    guide_thread_1 = None
    guide_thread_2 = None
    guide_thread_3 = None
    guide_thread_4 = None
    keep_running = True
    up_to_date = False
    monitor = xbmc.Monitor()
    db_path = os.path.join(ADDON_PATH_PROFILE, "epg.db")

    def __init__(self):
        init_db(self.db_path)
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
                #erase_stale_files(self.guide_path, today_timestamp)

                if VERBOSE:
                    xbmc.log('BuildGuide: Looping through guide days....')
                for guide_day in range(0, self.guide_days):
                    guide_date = now + timedelta(days=guide_day)
                    #guide_timestamp = str(guide_date.year) + str(guide_date.month).zfill(2) + str(guide_date.day).zfill(2)

                    self.guide_thread_1 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(guide_date, '1', self.db_path))
                    """
                    self.guide_thread_2 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(guide_date, '2', self.db_path))
                    self.guide_thread_3 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(guide_date, '3', self.db_path))
                    self.guide_thread_4 = threading.Thread(name='GuideThread',
                                                           target=guide_runner(guide_date, '4', self.db_path))
                    
                    thread_alive = True
                    while thread_alive:
                        thread_alive = False
                    
                        if self.guide_thread_1.isAlive() or self.guide_thread_2.isAlive() or self.guide_thread_3.isAlive() \
                                or self.guide_thread_4.isAlive():                    
                        if VERBOSE:
                            xbmc.log('BuildGuide: Active threads remain, waiting 5 seconds')
                    """

                if VERBOSE:
                    xbmc.log('BuildGuide: Guide up to date, going idle')

                self.up_to_date = True

                #now = datetime.now()
                #today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)
                #if not xbmcvfs.exists(os.path.join(self.guide_path, 'epg_' + today_timestamp + '_master.xml')):
                build_master_file(self.db_path, self.guide_path)

            #if now.minute == 0:
            if self.monitor.waitForAbort(600):
                break

            self.up_to_date = False

    def stop(self):
        if VERBOSE:
            xbmc.log('BuildGuide: Stop triggered....')

        self.keep_running = False
        self.join(0)