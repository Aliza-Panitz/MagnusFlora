#!/usr/bin/env python3
"""
Example for aiohttp.web basic server
Uses a background timer to read from a file to update a shared datastructure
Because it's going to be used as a simulator

Made available under the MIT license as follows:

Copyright 2017 Brian Bulkowski brian@bulkowski.org

Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
and associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or 
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING 
BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import threading
import time
import datetime
import os
import itertools

import json

import asyncio
import textwrap

from aiohttp import web


# Relay class 
class Relay:
    def __init__(self):
        # 1 is "NO and NC", 0 is "Flipped"
        self.state = 0

        # 0, 1, 2, 3 are possible
        # 1 = relay is NC /NO when portal is controlled, reversed when neutral
        # 2 = relay is reversed when portal is controlled, NO/NC when neutral
        # 3 = relay is NC /NO when portal is controlled, reversed for 3 seconds when faction changes, then reverts to NO/NC
        # 4 = relay closed when portal is controlled, reversed for 1.5 seconds
        self.mode = 0


# todo: since a mod has an owner, should make it a class as well, for parallelism sake


# Resonator class... because portals have more than one resonator

class Resonator:
    def __init__(self, position):
        # print ("Resonator create: position ",position)
        self.level = 0
        self.health = 0
        self.distance = 0
        self.position = position
        # print ("Resontaor level: ",self.level)

    def check(self):
        if type(self.level) is not int:
            return False
        if self.level < 0 or self.level > 8:
            return False
        if self.health is not int:
            return False
        if self.health < 0 or self.health > 100:
            return False
        if type(self.position) is not str:
            return False
        if self.position not in valid_positions:
            return False
        if self.distance is not int:
            return False
        if self.distance < 0 or self.distance > 100:
            return False
        return True

    def setLevel(self, level):
        # wire up debugging....
        if level > 8:
            return False
        if level < 0:
            return False
        self.level = level
        if level == 0:
            self.health = 0
            self.distance = 0
        return True

    def setHealth(self, health):
        if health > 100:
            return False
        if health < 0:
            return False
        self.health = health
        if health == 0:
            self.level = 0
            self.distance = 0
        return True

    def __str__(self):
        print (" grabbing reso string: level ",self.level)
        l = self.level
        return '{{"level": {0}, "health": {1}, "distance": {2}, "position": "{3}"\}}'.format(self.level, self.health, self.distance, self.position)

    # without the position, sometimes that is implied 
    def toBetterStr(self):
        return "{{\"level\": {0!s}, \"health\": {1!s}, \"distance\": {2!s} }}".format(self.level, self.health, self.distance)

# WARNING! This class has multithreaded access.
# Before you access the data structure, grab the lock and release afterward
# do not do anything blocking under the lock
class Portal:

    valid_positions = [ "E", "NE", "N", "NW", "W", "SW", "S", "SE" ]
    valid_mods = ["FA","HS-C","HS-R","HS-VR","LA-R","LA-VR","SBUL","MH-C","MH-R","MH-VR","PM","PS-C","PS-R","PS-VR","AXA","T"]

    def __init__(self, id_):
        self.faction = 0
        self.health = 0
        self.level = 0
        self.id_ = id_
        self.title = "default portal"
        self.owner = ""
        self.owner_id = 0
        self.resonators = { "N": Resonator("N"),
                            "NE": Resonator("NE"),
                            "E": Resonator("E"),
                            "SE": Resonator("SE"),
                            "S": Resonator("S"), 
                            "SW": Resonator("SW"), 
                            "W": Resonator("W"),
                            "NW": Resonator("NW") 
        }
        self.links = []
        self.mods = [ None, None, None, None ]
        self.lock = threading.Lock()  
        self.create_time = time.time()
        print("Created a new portal object")  

    # This function takes a Json object
    def setStatus( self, jsonStr ):
        print("Portal set status using string: ",jsonStr)
        try:
            statusObj = json.loads(jsonStr)
        except Exception as ex:
            template = "Exception in Portal parsing the json string {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print( message )
            return None

        print(" parsed JSON. Object is: ",statusObj)

        return

    # This is the "current form" that is mussing a lot of information
    def statusLegacy(self):
        resos = []
        resos.append('resonators: [')
        print (" resonators: ")
        for k, v in self.resonators.items():
            # skip if empty, saving space & time
            print(" r position ",k," value ",str(v))
            if v.level == 0:
                continue
            resos.append(str(v))
        resos.append(']')
        reso_string = ''.join(resos)
        return '"controllingFaction": {0}, "health": {1}, "level": {2}, "title": "{3}", "resonators": {4}'.format( 
            self.faction, self.health, self.level, self.title, reso_string )

    def __str__(self):
        # shortcut
        if level == 0:
            if level == 0:
                return '"faction": 0, "health":0, "level":0, "title":{0}, "resonators": []'.format(self.title)
        #longcut
        resos = []
        resos.append('resonators: [')
        for r in self.resonators:
            # skip if empty, saving space & time
            if r.level == 0:
                continue
            resos.append(r.toBetterStr())
        resos.append(']')
        reso_string = ''.join(resos)
        return '"faction": {0}, "health": {1}, "level": {2}, "title": "{3}", "resonators": {4}'.format( 
            self.faction, self.health, self.level, self.title, reso_string )

    # this method makes sure the status is valid and reasonable ( no values greater than game state )
    def check(self):
        if type(self.faction) is not int:
            print("Portal faction type initvalid")
            return False
        if self.faction < 0 or self.faction > 2:
            print("Illegal Portal faction value ",self.faction)
            return False
        if type(self.health) is not int:
            print("Portal health type invalid")
            return False
        if self.health < 0 or self.health > 100:
            print("Illegal Portal health value ",self.health)
            return False
        if type(self.level) is not int:
            print("Portal level type invalid")
            return False
        if self.health < 0 or self.health > 8:
            print("Illegal Portal level value ",self.level)
            return False
        if type(self.title) is not str:
            print("Portal title type invalid")
            return False
        if len(self.title) > 300:
            print("Portal title seems too long")
            return False
        if type(self.resonators) is not dict:
            print("Portal resonator type wrong")
            return False
        if len(self.resonators) != 8:
            print("Portal has incorrect number of resonators ",len(self.resontaors))
            return False
        for r in valid_positions:
            if checkResontaor(self.resonator[r]) == False:
                print(" resonator ",r," is not valid ")
                return False
        if type(self.mods) is not list:
            print("Mods wrong type")
            return False
        if len(self.mods) > 4:
            print("too many mods")
            return False
        for m in mods:
            if type(m) is not str:
                print (" type of one of the mods is wrong ")
                return False
            if m not in valid_mods:
                print ("invalid mod ",m)
                return False
        return True


#
# Background file processor
# 1. Open a file
# 2. Readline and set initial based on readline



@asyncio.coroutine
async def ticker(app):

    # file object
    f = None

    for i in itertools.count():
        portal = app['portal']

        # if no file object oepn one
        if f == None:
            try:
                fn = "portal_driver.json"
                f = open(fn, 'r')
                print("file object is ",f)

            except FileNotFoundError:
                # the most likely error
                print(" file ",fn," was not found, trying again later")
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print( message )

        # if file object, read and jam it into the status object
        if f != None:
            l = f.readline()
            l = l.rstrip()
            l = l.lstrip()

            if (type(l) == str and len(l) > 0):
                print(" first character is: ",l[0])
                if (l[0] == '#'):
                    print("ignoring comment line")
                else:
                    portal.setStatus(l)

        print(i)
        await asyncio.sleep(2)

#
# A number of debug / demo endpoints
# Note to self: you create a "Response" object, thn
# you manipulate it.


async def statusFaction(request):
    portal = request.app['portal']
    faction = 0
    with portal.lock:
        faction = portal.faction
    return web.Response(text=str(faction))

async def statusHealth(request):
    portal = request.app['portal']
    health = 0
    with portal.lock:
        health = portal.health
    return web.Response(text=str(health))

# this needs UTF8 because names might have utf8
async def statusJson(request):
    portal = request.app['portal']
    portal_str = ""
    with portal.lock:
        portal_str = str(portal)
    return web.Response(text=portal_str , charset='utf-8')

async def statusJsonLegacy(request):
    portal = request.app['portal']
    portal_str = ""
    with portal.lock:
        portal_str = portal.statusLegacy()
    return web.Response(text=portal_str , charset='utf-8')

async def hello(request):
    return web.Response(text="Hello World!")


# background tasks are covered near the bottom of this:
# http://aiohttp.readthedocs.io/en/stable/web.html
# Whatever tasks you create here will be executed and cancelled properly

async def start_background_tasks(app):
    app['file_task'] = app.loop.create_task( ticker(app))


async def cleanup_background_tasks(app):
    app['file_task'].cancel()
    await app['file_task']

##
##
##

async def init(loop):
    app = web.Application()
    app.router.add_get('/', hello)

    app.router.add_get('/status/faction', statusFaction)
    app.router.add_get('/status/health', statusHealth)
    app.router.add_get('/status/json', statusJson)
    app.router.add_get('/status/jsonLegacy', statusJsonLegacy)

    # create the shared objects
    app['portal'] = Portal(1)
    app['relay'] = Relay()

    # background tasks are covered near the bottom of this:
    # http://aiohttp.readthedocs.io/en/stable/web.html
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app

# register all the async stuff
loop = asyncio.get_event_loop()
app = loop.run_until_complete(init(loop))
print("registered app loop")

# run the web server
web.run_app(app, port=5050)
