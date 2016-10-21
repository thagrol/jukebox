#!/usr/bin/env python

import socket
import time
from threading import Thread

#debug = True
debug = False

def main():
    global debug    
    # edit mpd_host and mpd_port as needed
    mpd_host = "localhost"
    mpd_port = 6600
    
    # edit LCDd_host, LCDd_port and LCDd_keys as needed
    LCDd_host = "localhost"
    LCDd_port = 13666
    LCDd_keys=["Up","Down","Enter","Escape"]

    # get host IP addresses
    LCDd_hostip = socket.gethostbyname(LCDd_host)
    mpd_hostip = socket.gethostbyname(mpd_host)
    
    # map mpd commands to LCDd keys
    # currently set as follows for CrystalFontz CFA-631
    #   Top Left     - Play/Pause
    #   Top Right    - Spare
    #   Bottom Left  - Previous Track
    #   Bottom Right - Next Track
    mpd_next = 3
    mpd_prev = 1
    mpd_playpause = 0
    mpd_spare = 2

    # display backlight
    backlighton = True

    # give LCDd some time to come up
    time.sleep(10)

    # create socket and connect to LCDd
    LCDd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "attmepting to connect to LCDd on ", LCDd_hostip, " ", LCDd_port
    LCDd.connect((LCDd_hostip, LCDd_port))
    print "    connected"

    # basic LCDd setup
    LCDd.sendall("hello\n")
    incoming = LCDd.recv(1024) # returned data is largely irrelevant so going to ignore it
    LCDd.sendall("client_set -name mpd-remote\n")
    incoming = LCDd.recv(1024) # don't really care what this is but need to clear it
    for k in LCDd_keys:
        # need to grab keys in exclusive mode so we get them without needing a screen to be visible
        cmd = "client_add_key -exclusively " + k + "\n"
        LCDd.sendall(cmd)
        incoming = LCDd.recv(1024) # don't really care what this is but need to clear it
    # setup blanking screen
    LCDd.sendall("screen_add blank\n")
    LCDd.sendall("screen_set blank -priority hidden\n")
    LCDd.sendall("screen_set blank -backlight off\n")

    # loop forever to get button events
    looping = True
    while looping:
        incoming = LCDd.recv(1024) #this will block waiting on data
        if len(incoming) == 0:
            looping = False
        for l in incoming.splitlines():
            if debug:
                print l
            if l == "key " + LCDd_keys[mpd_next]:
                #send next command to mpd
                #send_mpd_cmd(mpd_hostip, mpd_port, "next")
                t = Thread(target=send_mpd_cmd, args=(mpd_hostip, mpd_port, "next"))
                t.start()
            if l == "key " + LCDd_keys[mpd_prev]:
                #send prev command to mpd
                #send_mpd_cmd(mpd_hostip, mpd_port, "previous")
                t = Thread(target=send_mpd_cmd, args=(mpd_hostip, mpd_port, "previous"))
                t.start()
            if l == "key " + LCDd_keys[mpd_playpause]:
                #send pause command to mpd
                #send_mpd_cmd(mpd_hostip, mpd_port, "pause")
                t = Thread(target=send_mpd_cmd, args=(mpd_hostip, mpd_port, "pause"))
                t.start()
            if l == "key " + LCDd_keys[mpd_spare]:
                #do whatever
                if backlighton:
                    LCDd.sendall("screen_set blank -priority 1\n")
                    t = Thread(target=send_mpd_cmd, args=(mpd_hostip, mpd_port, "stop"))
                    t.start()
                    backlighton = False
                else:
                    LCDd.sendall("screen_set blank -priority hidden\n")
                    t = Thread(target=send_mpd_cmd, args=(mpd_hostip, mpd_port, "play"))
                    t.start()
                    backlighton = True
                if debug:
                    looping = False

    LCDd.close()

def send_mpd_cmd(host, port, cmd):
    # send command to mpd
    # the sendall may block so might be better in a seperate thread

    global debug
    try:
        mpd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mpd.connect((host, port))
        mpd.sendall(cmd + "\n")
        mpd.close
    except:
        # quietly ignore it
        if debug:
            raise
        else:
            pass

if __name__ == "__main__":
    main()
