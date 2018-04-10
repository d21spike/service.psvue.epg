import threading
import xbmc, xbmcgui, xbmcaddon
import os
import datetime
import glob

ADDON = xbmcaddon.Addon()
PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
VERIFY = False


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


def guide_runner(guide_path, guide_timestamp, guide_sequence):
    xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + ' Started - > Guide Path: ' + str(guide_path) +
             ' | Guide Timestamp: ' + guide_timestamp + ' | ' + guide_sequence)

    if not os.path.isdir(guide_path):
        os.mkdir(guide_path)

    guide_file = 'epg_' + guide_timestamp + '_' + guide_sequence + '.xml'

    if not os.path.exists(guide_path + guide_file):
        xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + 'Creating guide file: ' + guide_file)
        file = open(guide_path + guide_file, 'w')
        build_guide_file(file, guide_sequence)
        file.close()
    else:
        xbmc.log('BuildGuide Thread ' + guide_sequence + ': ' + 'File ' + guide_file + ' already exists, exiting.')


def build_guide_file(file, guide_sequence):
    xbmc.log('Code to populate guide file will go here.')


def erase_stale_files(guide_path, today_timestamp):
    xbmc.log('BuildGuide: Inside ' + guide_path + '\nwill delete anything older than ' + today_timestamp)
    files = glob.glob(guide_path + '*.xml')

    if files:
        for file_path in files:
            try:
                file = file_path.rsplit('\\', 1)[1]
                file_timestamp = find(file, 'epg_', '_')
                if file_timestamp < today_timestamp:
                    xbmc.log('BuildGuide: ' + file + ' is older than ' + today_timestamp + ', will delete...')
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        xbmc.log('BuildGuide: Failed to delete old guide file -> ' + file_path + '\nException:' + e)
                else:
                    xbmc.log('BuildGuide: ' + file + ' is current, ignoring.')

            except Exception as e:
                xbmc.log('BuildGuide: failed to retrieve file for checking: ' + str(e))

    else:
        xbmc.log('BuildGuide: Directory is empty, nothing to delete')

    return


class BuildGuide(threading.Thread):
    guide_days = 3
    guide_path = os.path.join(ADDON_PATH_PROFILE, "epg") + '\\'
    guide_thread_1 = None
    guide_thread_2 = None
    guide_thread_3 = None
    guide_thread_4 = None
    keep_running = True

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        xbmc.log('BuildGuide: Thread starting....')

        while self.keep_running:
            now = datetime.datetime.now()
            today_timestamp = str(now.year) + str(now.month).zfill(2) + str(now.day).zfill(2)

            xbmc.log('BuildGuide: Erasing stale files....')
            erase_stale_files(self.guide_path, today_timestamp)

            xbmc.log('BuildGuide: Looping through guide days....')
            for guide_day in range(0, self.guide_days):
                guide_date = now + datetime.timedelta(guide_day)
                guide_timestamp = str(guide_date.year) + str(guide_date.month).zfill(2) + str(guide_date.day).zfill(2)

                self.guide_thread_1 = threading.Thread(name='GuideThread',
                                                 target=guide_runner(self.guide_path, guide_timestamp,
                                                                     '1'))
                self.guide_thread_2 = threading.Thread(name='GuideThread',
                                                     target=guide_runner(self.guide_path,
                                                                         guide_timestamp,
                                                                         '2'))
                self.guide_thread_3 = threading.Thread(name='GuideThread',
                                                     target=guide_runner(self.guide_path,
                                                                         guide_timestamp,
                                                                         '3'))
                self.guide_thread_4 = threading.Thread(name='GuideThread',
                                                     target=guide_runner(self.guide_path,
                                                                         guide_timestamp,
                                                                         '4'))

                thread_alive = True
                while thread_alive:
                    thread_alive = False
                    if self.guide_thread_1.isAlive() or self.guide_thread_2.isAlive() or self.guide_thread_3.isAlive() \
                            or self.guide_thread_4.isAlive():
                        thread_alive = True
                    xbmc.log('BuildGuide: Active threads remain, waiting 5 seconds')
                    sleep(5, 's')

            xbmc.log('BuildGuide: Finish updating guide files, will wait till next day.')
            time_to_wait = (60 * (24 - now.hour)) + (60 - now.minute) + 1
            # sleep(time_to_wait, 'M')

    def stop(self):
        xbmc.log('BuildGuide: Stop triggered....')
        self.keep_running = False
        self.join(0)