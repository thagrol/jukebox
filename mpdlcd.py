#!/usr/bin/env python

import socket
import time
import select
import logging
from time import sleep

logging.basicConfig(level = logging.DEBUG)
logging.debug('Starting mpdctl')

# lcdproc stuff
LCDd_HOSTNAME = 'localhost' # change as needed
LCDd_PORT = 13666 # default LCDd port
LCDd_COLUMNS = 20
LCDd_ROWS = 2
# screen & widget names
LCDd_CLIENTNAME = 'mpdlcd.py'
LCDd_MPDSTATUS = '_mpdstatus'
LCDd_MPDREPEAT = '_mpdrepeat'
LCDd_MPDRANDOM = '_mpdrandom'
LCDd_MPDCURSONG = '_mpdcursong'
# command strings
LCDd_SETREPEATON = 'widget_set %s %s 1 1 "R"\n' % (LCDd_MPDSTATUS, LCDd_MPDREPEAT)
LCDd_SETREPEATOff = 'widget_set %s %s 1 1 " "\n' % (LCDd_MPDSTATUS, LCDd_MPDREPEAT)
LCDd_SETRANDOMON = 'widget_set %s %s 3 1 "S"\n' % (LCDd_MPDSTATUS, LCDd_MPDRANDOM)
LCDd_SETRANDOMOFF = 'widget_set %s %s 3 1 " "\n' % (LCDd_MPDSTATUS, LCDd_MPDRANDOM )
LCDd_SETCURSONG = 'widget_set %s %s 1 2 %s 2 m 02 "%s        "\n' %(LCDd_MPDSTATUS, LCDd_MPDCURSONG, LCDd_COLUMNS, '%s')

# mpd stuff
MPD_HOSTNAME = 'localhost' # change this as needed
MPD_PORT = 6600 #default mpd port
MPD_IDLECMD = 'idle player options\n'

# now start doing some stuff
# initialise flags & buffers
lcdd_sendbuffer = ''
lcdd_recvbuffer = ''
mpd_sendbuffer = ''
mpd_recvbuffer = ''
lcdd_backlighton = True
mpd_play = False
mpd_random = False
mpd_repeat = False
mpd_songinfo = ''

# create sockets
lcdd_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mpd_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect sockets
max_retries = 3 # max retries when attempting to connect to server

# LCDd
lcdd_soc.settimeout(5) # 5 second timeout while attempting conection
lcdd_connected = False
lcdd_ip = None
retries = 0
while lcdd_connected == False and retries < max_retries:
    if lcdd_ip == None:
        try:
            lcdd_ip = socket.gethostbyname(LCDd_HOSTNAME)
        except KeyboardInterrupt:
                raise
        except Exception:
            lcdd_connected = False
            retries += 1
            continue
    try:
        lcdd_soc.connect((lcdd_ip, LCDd_PORT))
    except KeyboardInterrupt:
            raise
    except Exception:
        lcdd_connected = False
        retries += 1
        continue
    else:
        lcdd_connected = True
if lcdd_connected == False:
    lcdd_soc.close()

# mpd
mpd_soc.settimeout(5) # 5 second timeout while attempting conection
mpd_connected = False
mpd_ip = None
retries = 0
while mpd_connected == False and retries < max_retries:
    if mpd_ip == None:
        try:
            mpd_ip = socket.gethostbyname(MPD_HOSTNAME)
        except Exception:
            mpd_connected = False
            retries += 1
            continue
    try:
        mpd_soc.connect((mpd_ip, MPD_PORT))
    except Exception:
        mpd_connected = False
        retries += 1
    else:
        mpd_connected = True
if mpd_connected == False:
    mpd_soc.close()

# did we connect to both sockets?
if lcdd_connected and mpd_connected:
    pass
else:
    logging.critical('Failed to open connections to LCDd and/or mpd. Exiting')
    quit() # failed to open both sockets

# setup socket checklist
soc_checklist = []
if lcdd_connected:
    soc_checklist.append(lcdd_soc)
if mpd_connected:
    soc_checklist.append(mpd_soc)

# put LCDd screen setup commands into buffer
#   init connection
lcdd_sendbuffer = 'hello\n'
#   set client name
lcdd_sendbuffer += 'client_set -name %s\n' % LCDd_CLIENTNAME
#   add mpd status screen
lcdd_sendbuffer += 'screen_add %s\n' % LCDd_MPDSTATUS
lcdd_sendbuffer += 'screen_set %s -backlight on\n' % LCDd_MPDSTATUS
lcdd_sendbuffer += 'screen_set %s -heartbeat off\n' % LCDd_MPDSTATUS
#     add repeat indicator
lcdd_sendbuffer += 'widget_add %s %s string\n' % (LCDd_MPDSTATUS, LCDd_MPDREPEAT)
#     add random indicator
lcdd_sendbuffer += 'widget_add %s %s string\n' % (LCDd_MPDSTATUS, LCDd_MPDRANDOM)
#     add current song info
lcdd_sendbuffer += 'widget_add %s %s scroller\n' % (LCDd_MPDSTATUS, LCDd_MPDCURSONG)

# get mpd status
mpd_soc.sendall('status\n')
while mpd_recvbuffer.endswith('OK\n') == False:
    try:
        mpd_recvbuffer += mpd_soc.recv(4096)
    except socket.timeout:
        pass

for l in mpd_recvbuffer.splitlines():
    l = l.lower()
    if l.startswith('repeat: '):
        l = l[len('repeat: '):]
        mpd_repeat = bool(int(l))
    if l.startswith('random: '):
        l = l[len('random: '):]
        mpd_random = bool(int(l))
    if l.startswith('state: '):
        l = l[len('state: '):]
        if l =='play':
            mpd_play = True
        else:
            mpd_play = False

# get current song info
mpd_recvbuffer = ''
mpd_soc.sendall('currentsong\n')
while mpd_recvbuffer.endswith('OK\n') == False:
    try:
        mpd_recvbuffer += mpd_soc.recv(4096)
    except socket.timeout:
        pass

cur_artist = 'Unknown'
cur_title = cur_artist
mpd_songid = None
for l in mpd_recvbuffer.splitlines():
    ll = l.lower()
    if ll.startswith('artist: '):
        cur_artist = l[len('artist: '):]
    if ll.startswith('title: '):
        cur_title = l[len('title: '):]
    if ll.startswith('id: '):
        mpd_songid = l[len('id: '):]
newsongid = mpd_songid
mpd_songinfo = cur_artist + ' - ' + cur_title
cur_artist = None
cur_title = None

# insert widget updates int LCDd buffer
lcdd_sendbuffer += LCDd_SETCURSONG % mpd_songinfo
if mpd_repeat:
    lcdd_sendbuffer += LCDd_SETREPEATON
else:
    lcdd_sendbuffer += LCDd_SETREPEATOFF
if mpd_random:
    lcdd_sendbuffer += LCDd_SETRANDOMON
else:
    lcdd_sendbuffer += LCDd_SETRANDOMOFF

# insert idle command in mpd buffer
mpd_sendbuffer = MPD_IDLECMD

# switch to non blocking sockets and enter main polling loop
for s in soc_checklist:
    s.setblocking(0)

while True:
    sleep(0.25) # don't want to eat all cpu time
    readable, writeable, broken = select.select(soc_checklist, soc_checklist, [], 0)
    # writeable sockets
    for s in writeable:
        if s == lcdd_soc and len(lcdd_sendbuffer) > 0:
            sent = s.send(lcdd_sendbuffer)
            lcdd_sendbuffer = lcdd_sendbuffer[sent:] # remove sent stuff from buffer
        if s == mpd_soc and len(mpd_sendbuffer) > 0:
            sent = s.send(mpd_sendbuffer)
            logging.debug('sent to mpd: ' + mpd_sendbuffer[:sent])
            mpd_sendbuffer = mpd_sendbuffer[sent:] # remove sent stuff from buffer
    # readable sockets
    for s in readable:
        if s == lcdd_soc or len(lcdd_recvbuffer) > 0: # incoming messaged from lcdproc(LCDd)
            if s == lcdd_soc:
                lcdd_recvbuffer += lcdd_soc.recv(4096)
            for l in lcdd_recvbuffer.splitlines(True):
                if l.endswith('\n'):
                    # lcdd terminates all message with \n so only the last line can fail this test
                    #remove processed input from buffer
                    lcdd_recvbuffer = lcdd_recvbuffer[len(l):]
                else:
                    break
        if s == mpd_soc or len(mpd_recvbuffer) > 0: # incoming messages from mpd
            if s == mpd_soc:
                mpd_recvbuffer += mpd_soc.recv(4096)
            for l in mpd_recvbuffer.splitlines(True):
                logging.debug('mpd: ' + l)
                if l.endswith('\n'):
                    ll = l.lower()
                    ll = ll[:-1] # strip trailing \n
                    if ll.startswith('changed'):
                        if 'options' in ll:
                            mpd_sendbuffer += 'status\n'
                        if 'player' in ll:
                            mpd_sendbuffer += 'currentsong\n'
                        mpd_sendbuffer += MPD_IDLECMD
                    if  ll.startswith('id: '):
                        newsongid = ll[len('id: '):]
                    if ll.startswith('repeat: '):
                        newrepeat = bool(int(l[len('repeat: '):]))
                        if newrepeat != mpd_repeat:
                            if newrepeat:
                                lcdd_sendbuffer += LCDd_REPEATON
                            else:
                                lcdd_sendbuffer += LCDd_REPEATOFF
                            mpd_repeat = newrepeat
                    if ll.startswith('random: '):
                        newrandom = bool(int(l[len('random: '):]))
                        if newrandom != mpd_random:
                            if newrandom:
                                lcdd_sendbuffer += LCDd_RANDOMON
                            else:
                                lcdd_sendbuffer += LCDd_RANDOMOFF
                            mpd_random = newrandom
                    if ll.startswith('artist: '):
                        cur_artist = l[len('artist: '):-1]
                        logging.debug('artist from mpd: ' + str(cur_artist))
                    if ll.startswith('title: '):
                        cur_title = l[len('title: '):-1]
                        logging.debug('title from mpd: ' + str(cur_title))
                    #remove processed input from buffer
                    mpd_recvbuffer = mpd_recvbuffer[len(l):]
                else:
                    break
                if newsongid != mpd_songid and cur_artist != None and cur_title != None:
                    mpd_songinfo = cur_artist + ' - ' + cur_title
                    logging.debug('new song: ' + mpd_songinfo)
                    mpd_songid = newsongid
                    logging.debug(LCDd_SETCURSONG % mpd_songinfo + '+++')
                    lcdd_sendbuffer += LCDd_SETCURSONG % mpd_songinfo
                    cur_artist = None
                    cur_title = None

