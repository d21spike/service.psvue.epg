import threading
import thread
import xbmc, xbmcgui, xbmcaddon
import requests, urllib
import cookielib
import Cookie
import os
import sys
import base64
import re
import time
import traceback
import socket
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import parse_qs
from urllib import *

ADDON = xbmcaddon.Addon()
PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
VERIFY = False


def load_cookies():
    cookie_file = os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp')
    cj = cookielib.LWPCookieJar()
    try:
        cj.load(cookie_file, ignore_discard=True)
    except:
        pass

    return cj


def epg_get_stream(url):
    headers = {
        'Accept': '*/*',
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://vue.playstation.com',
        'Accept-Language': 'en-US,en;q=0.8',
        'Referer': 'https://vue.playstation.com/watch/live',
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': UA_ANDROID_TV,
        'Connection': 'Keep-Alive',
        'Host': 'media-framework.totsuko.tv',
        'reqPayload': PS_VUE_ADDON.getSetting(id='EPGreqPayload'),
        'X-Requested-With': 'com.snei.vue.android'
    }

    r = requests.get(url, headers=headers, cookies=load_cookies(), verify=VERIFY)
    json_source = r.json()
    stream_url = json_source['body']['video']

    return stream_url


def find(source, start_str, end_str):
    start = source.find(start_str)
    end = source.find(end_str, start + len(start_str))
    if start != -1:
        return source[start + len(start_str):end]
    else:
        return ''


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(server):
        xbmc.log("WebServer: Get request Received")

        ##########################################################################################
        # Stream preparation chunk
        ##########################################################################################

        # Extract channel url from request URI
        parameters = parse_qs(server.path[7:])
        channel_url = urllib.unquote(str(parameters['params'][0]))
        xbmc.log("Received Channel URL: " + channel_url)

        # Retrieve stream master file url for channel
        stream_url = epg_get_stream(channel_url)
        xbmc.log("Retrieved Stream URL: " + stream_url)

        xbmc.log("Retrieving Master File")
        response = requests.get(stream_url, headers="", cookies=load_cookies(), verify=VERIFY)
        response_code = response.status_code
        response_headers = response.headers
        response_content = response.text

        # Inject master file HOST into stream URLs
        master_file = ''
        last_stream = ''
        line = re.compile("(.+?)\n").findall(response_content)
        for temp in line:
            if '#EXT' not in temp:
                if 'http' not in temp:
                    temp = stream_url.replace(stream_url.rsplit('/', 1)[-1], temp)
                    last_stream = temp
            master_file += temp + '\n'
        xbmc.log('New Master File: ' + master_file)

        ##########################################################################################
        # Request response chunk
        ##########################################################################################

        # Response code for the get request
        # 200 OK
        # 202 Accepted
        # 301 Moved Permanently
        # 302 Found
        # 303 See Other
        # 308 Permanent Redirect
        server.send_response(303)

        # Header array for the response, toggle Connection Close or Keep/Alive depending on the reponse code
        headers = {
            'Content-type': 'text/html;charset=utf-8',
            'Connection': 'close',
            'Host': 'media-framework.totsuko.tv',
            'Location': last_stream,
            'Set-Cookie': 'reqPayload=' + PS_VUE_ADDON.getSetting(id='EPGreqPayload') + '; Domain=totsuko.tv; Path=/'
        }

        # Loop through the Header Array sending each one individually
        for key in headers:
            try:
                value = headers[key]
                server.send_header(key, value)
            except Exception, e:
                xbmc.log(e)
                pass

        # Tells the server the headers are done and the body can be started
        server.end_headers()

        # Write body content to the response
        # server.wfile.write(master_file)

        # Close the server response file
        server.wfile.close()


class Server(HTTPServer):
    def get_request(self):
        self.socket.settimeout(5.0)
        result = None
        while result is None:
            try:
                result = self.socket.accept()
            except socket.timeout:
                pass
        result[0].settimeout(1000)
        return result


class ThreadedHTTPServer(ThreadingMixIn, Server):
    """Handle requests in a separate thread."""


class PSVueWebService(threading.Thread):
    httpd = None
    hostname = '127.0.0.1'
    port = 54321

    def __init__(self):

        if ADDON.getSetting(id='port') == '':
            dialog = xbmcgui.Dialog()
            dialog.notification('PS Vue EPG', 'Please enter a port number in the PS Vue EPG Build Settings',
                                xbmcgui.NOTIFICATION_INFO, 5000, False)
            sys.exit()
        else:
            self.port = ADDON.getSetting(id='port')

        if self.httpd == None:
            socket.setdefaulttimeout(10)
            server_class = ThreadedHTTPServer
            xbmc.log('Initialized WebServer Hostname | Port -> ' + self.hostname + ' | ' + str(self.port))
            self.httpd = server_class((self.hostname, int(self.port)), RequestHandler)
        else:
            self.httpd.handle_request()

        threading.Thread.__init__(self)

    def run(self):
        xbmc.log("WebServer Started - %s:%s" % (self.hostname, self.port))
        self.httpd.serve_forever()
        self.httpd.handle_request()

    def stop(self):
        try:
            self.httpd.server_close()
            xbmc.log("WebServer Stopped %s:%s" % (self.hostname, self.port))
        except:
            pass

        self.join(0)