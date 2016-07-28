#!/usr/bin/env python
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
"""

import os
import re
import json
import struct
import logging
import requests
import argparse
import pprint
import time
import random
import threading
from math import sqrt

from pgoapi import PGoApi
from pgoapi.utilities import *
from POGOProtos.Enums_pb2 import PokemonId
from POGOProtos.Inventory_pb2 import ItemId
from POGOProtos.Networking.Responses_pb2 import FortSearchResponse, CatchPokemonResponse


from util import *


log = logging.getLogger(__name__)

razzBerryItemId = ItemId.Value("ITEM_RAZZ_BERRY")

class PokeBot(object):
    """docstring for PokeBot"""

    api = PGoApi()
    forts = {}
    fortCountdowns = {}
    currentTargetId = None
    originalPosition = None
    run_event = threading.Event()
    thread = None
    cellInfos = {}
    inventory = {1:0,2:0,3:0}
    pokemons = {}

    actions = []

    def __init__(self):
        self.run_event.clear()
        super(PokeBot, self).__init__()
    
    def login(self, provider, username, password, loc):
        self.originalPosition = get_pos_by_name(loc)
        self.api.set_position(*self.originalPosition)
        return self.api.login(provider, username, password)

    def running(self):
        return self.run_event.is_set()

    def start(self, detach=False, speedFactor = 1):
        self.updateInventory()
        if detach:
            self.thread = threading.Thread(target=self.start, args=(False,speedFactor))
            self.thread.start()
            return
        else:
            if self.run_event.is_set():
                self.run_event.clear()
                self.thread.join()
            self.thread = threading.current_thread()
        self.run_event.set()

        worker = self.walkWorker()
        while self.run_event.is_set():
            time.sleep(random.uniform(0.8/speedFactor, 1.2/speedFactor))
            self.timeTick(speedFactor)
            self.updatePosition()
            worker.next()

    def stop(self):
        if self.run_event.is_set():
            self.run_event.clear()
            self.thread.join()

    def chooseFort(self):
        (x, y, z) = self.api.get_normal_position()
        minDist = 20
        rtn = None
        for fid, fort in self.forts.iteritems():
            if fid not in self.fortCountdowns:
                curDist = sqrt(abs(self.forts[fid]["latitude"] - x) ** 2 + abs(self.forts[fid]["longitude"] - y) ** 2)
                if "lure_info" in fort:
                    curDist -= 0.0005
                if curDist < minDist:
                    minDist = curDist
                    rtn = fid
        if rtn != None:
            return rtn
        if len(self.forts) > 0:
            return random.choice(self.forts.keys())
        return None

    refreshInventoryCountdown = 100
    _refreshCountdown = None
    def timeTick(self, speedFactor = 1):
        if self._refreshCountdown == None or self._refreshCountdown <= 0:
            self._refreshCountdown = speedFactor

            self.refreshInventoryCountdown -= 1
            tbr = []
            for fid in self.fortCountdowns.keys():
                self.fortCountdowns[fid] -= 1
                if self.fortCountdowns[fid] <= 0:
                    tbr.append(fid)
            for fid in tbr:
                del self.fortCountdowns[fid]

            if self.refreshInventoryCountdown <= 0:
                self.refreshInventoryCountdown = 200
                self.updateInventory()

        self._refreshCountdown -= 1

    def execute(self):
        response_dict = self.api.call()
        log.debug(pprint.PrettyPrinter(indent=1).pformat(response_dict))
        return response_dict

    def updateInventory(self):
        self.api.get_player().get_inventory()
        inventory_req = self.api.call()
        try:
            inventory_dict = inventory_req['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']
        except:
            inventory_dict = []
        for item in inventory_dict:
            try:
                item_id = item['inventory_item_data']['item']['item_id']
                item_count = item['inventory_item_data']['item']['count']
                self.inventory[item_id] = item_count
            except:
                pass
            try:
                pid = item['inventory_item_data']['pokemon_data']['id']
                pokemon_id = item['inventory_item_data']['pokemon_data']['pokemon_id']
                cp = item['inventory_item_data']['pokemon_data']['cp']
                if pokemon_id in self.pokemons:
                    self.pokemons[pokemon_id][pid] = cp
                else:
                    self.pokemons[pokemon_id] = {pid : cp}
            except:
                pass
        log.info("UPDATE_INVENTORY \n{}".format("\n".join([ItemId.Name(i)+" "+str(c) for i,c in self.inventory.iteritems()])))

    def updateMap(self):
        (x, y, z) = self.api.get_normal_position()
        cell_ids = get_cell_ids(x, y)
        timestamps = [0,]*len(cell_ids)
        self.api.get_map_objects(latitude=f2i(x), longitude=f2i(y), since_timestamp_ms=timestamps, cell_id=cell_ids)
        log.info("GET_MAP_OBJECTS at {}, {}".format(x,y))
        rd = self.execute()

        # trigger error if responses doesn't contain map_cells. bot will restart
        cells = rd["responses"]["GET_MAP_OBJECTS"]["map_cells"]
        pokemons = []

        for cell in cells:
            self.cellInfos[cell["s2_cell_id"]] = cell
            if "catchable_pokemons" in cell:
                for poke in cell["catchable_pokemons"]:
                    if "pokemon_id" in poke:
                        pokemons.append(poke)
            if "forts" in cell:
                for fort in cell["forts"]:
                    if "type" in fort:
                        self.forts[fort["id"]] = fort
        return pokemons

    def whichPokeball(self, cp):
        ball = None
        if self.inventory[1] > 0:
            ball = 1
        if self.inventory[2] > 0 and (cp > 300 or ball == None):
            ball = 2
        if self.inventory[3] > 0 and (cp > 800 or ball == None):
            ball = 3
        return ball

    def shouldUseBerry(self, cp):
        return cp > 300 and razzBerryItemId in self.inventory and self.inventory[razzBerryItemId] > 0

    def encounter(self, poke):
        encounter_result = 5
        if poke != None and "encounter_id" in poke and "spawnpoint_id" in poke and sum(self.inventory.values()) > 0:
            encounter_id = poke["encounter_id"]
            spawnpoint_id = poke["spawnpoint_id"]
            (x, y, z) = self.api.get_position()

            self.api.encounter(encounter_id=encounter_id,
                               spawnpoint_id=spawnpoint_id,
                               player_latitude=x, 
                               player_longitude=y)
            response_dict = self.execute()

            try:
                encounter_result = response_dict["responses"]["ENCOUNTER"]["status"]
            except:
                encounter_result = 5
            if encounter_result == 1:
                try:
                    poke["cp"] = response_dict["responses"]["ENCOUNTER"]["wild_pokemon"]["pokemon_data"]["cp"]
                except:
                    poke["cp"] = 1
                self.actions.append({"action":"encounter", "data":poke, "name": PokemonId.Name(poke["pokemon_id"])})
                log.info("A wild {} appeared! cp {}.".format(PokemonId.Name(poke["pokemon_id"]), poke["cp"]))
        return encounter_result == 1

    def catch(self, poke):
        catch_result = 5
        if poke != None and "encounter_id" in poke and "spawnpoint_id" in poke:
            encounter_id = poke["encounter_id"]
            spawnpoint_id = poke["spawnpoint_id"]
            pokeball = self.whichPokeball(poke["cp"])
            if pokeball == None:
                log.info("Out of Pokeball.")
                return False
            if self.shouldUseBerry(poke["cp"]):
                self.api.use_item_capture(item_id=razzBerryItemId, encounter_id=encounter_id, spawn_point_guid=spawnpoint_id )
                rd = self.execute()
                log.info("Used ITEM_RAZZ_BERRY.")
                self.actions.append({"action":"used", "name":"ITEM_RAZZ_BERRY"})
                self.inventory[razzBerryItemId] -= 1

            self.inventory[pokeball] -= 1
            log.info("Throw {}.".format(ItemId.Name(pokeball)))
            self.actions.append({"action":"used", "name":ItemId.Name(pokeball)})
            self.api.catch_pokemon(encounter_id=encounter_id,
                              spawn_point_guid=spawnpoint_id,
                              pokeball=pokeball,
                              normalized_reticle_size=random.uniform(1.5, 2),
                              hit_pokemon=1,
                              spin_modifier=1)
            response_dict = self.execute()

            try:
                catch_result = response_dict["responses"]["CATCH_POKEMON"]["status"]
            except:
                catch_result = 5
            self.actions.append({"action":"catch", "status":CatchPokemonResponse.CatchStatus.Name(catch_result), "data":poke, "name":PokemonId.Name(poke["pokemon_id"])})
            if catch_result == 1:
                log.info("Gotcha! {}, cp {}.".format(PokemonId.Name(poke["pokemon_id"]), poke["cp"]))
            else:
                log.info("{} {}!".format(PokemonId.Name(poke["pokemon_id"]), CatchPokemonResponse.CatchStatus.Name(catch_result)))
        return catch_result == 4

    def searchFort(self, fort):
        (x, y, z) = self.api.get_normal_position()
        if "id" in fort and fort["id"] not in self.fortCountdowns and abs(fort["latitude"] - x) < 0.0003 and abs(fort["longitude"] - y) < 0.0003:
            self.api.fort_search(fort_id=fort["id"], 
                            fort_latitude=fort["latitude"], 
                            fort_longitude=fort["longitude"], 
                            player_latitude=f2i(x), 
                            player_longitude=f2i(y))
            response_dict = self.execute()

            try:
                status = FortSearchResponse.Result.Name(response_dict["responses"]["FORT_SEARCH"]["result"])
                log.info("FORT_SEARCH {}".format(status))
                if "items_awarded" in response_dict["responses"]["FORT_SEARCH"]:
                    self.actions.append({"action":"fortSearch", "status":status, "items":names})
                else:
                    self.actions.append({"action":"fortSearch", "status":status})
                awards = response_dict["responses"]["FORT_SEARCH"]["items_awarded"]
                names = ", ".join([ItemId.Name(x["item_id"]) for x in awards])
                log.info("GOT {}".format(names))
                for x in awards:
                    if x["item_id"] in self.inventory:
                        self.inventory[x["item_id"]] += 1
                    else:
                        self.inventory[x["item_id"]] = 1
            except:
                pass
            self.fortCountdowns[fort["id"]] = 400
            return True
        return False

    def releaseItem(self):
        for item_id, count in self.inventory.iteritems():
            if count > 100 and item_id > 3:
                self.api.recycle_inventory_item(item_id=item_id, count = 50)
                self.execute()
                self.actions.append({"action":"throw", "item":ItemId.Name(item_id), "count":50})
                log.info("Throw away {} {}.".format(50, ItemId.Name(item_id)))
                self.inventory[item_id] -= 50
                return True
        return False

    def releasePokemon(self):
        for pokemon_id, pokemons in self.pokemons.iteritems():
            worstPoke = None
            minPokemonCp = 5000
            if len(pokemons) > 2:
                for poke, cp in pokemons.iteritems():
                    if cp < minPokemonCp:
                        worstPoke = poke
                        minPokemonCp = cp
            if worstPoke:
                log.info("Release {}, cp {}.".format(PokemonId.Name(pokemon_id), minPokemonCp))
                self.api.release_pokemon(pokemon_id = worstPoke)
                self.actions.append({"action":"release", "name":PokemonId.Name(pokemon_id), "cp":minPokemonCp})
                rd = self.execute()
                del self.pokemons[pokemon_id][worstPoke]
                return True
        return False

    def walkWorker(self):
        while True:
            # get map info
            pokemons = self.updateMap()

            for i in range(0,random.randint(5, 20)):
                yield

            bestPokemon = None
            maxPokemonId = -1

            for poke in pokemons:
                if poke["pokemon_id"] > maxPokemonId:
                    bestPokemon = poke
                    maxPokemonId = poke["pokemon_id"]
            
            for fid, fort in self.forts.iteritems():
                if self.searchFort(fort):
                    for i in range(0, random.randint(10, 20)):
                        yield


            if self.encounter(bestPokemon):
                for i in range(0,random.randint(10, 20)):
                    yield

                while self.catch(bestPokemon):
                    for i in range(0,random.randint(4, 8)):
                        yield
            else:
                for i in range(0,random.randint(15, 30)):
                    yield

            if self.releasePokemon():
                for i in range(0,random.randint(4, 8)):
                    yield

            if self.releaseItem():
                for i in range(0,random.randint(4, 8)):
                    yield

            for i in range(0,random.randint(5, 10)):
                yield

    def updatePosition(self):
        if self.currentTargetId == None:
            self.currentTargetId = self.chooseFort()
        else:
            step = 0.00001
            (tx, ty) = (self.forts[self.currentTargetId]["latitude"], self.forts[self.currentTargetId]["longitude"])
            (x, y, z) = self.api.get_normal_position()
            if x == tx and y == ty:
                self.currentTargetId = self.chooseFort()
                return

            if x != tx:
                x += min(step, tx - x) if tx > x else -min(step, x - tx)
            if y != ty:
                y += min(step, ty - y) if ty > y else -min(step, y - ty)
            self.api.set_position(x,y,z)


    
def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",
        required=required("auth_service"))
    parser.add_argument("-u", "--username", help="Username", required=required("username"))
    parser.add_argument("-p", "--password", help="Password", required=required("password"))
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-s", "--speed", help="Speed Factor", type=float)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
    parser.set_defaults(DEBUG=False, TEST=False, speed=1)
    config = parser.parse_args()

    # Passed in arguments shoud trump
    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = load[key]

    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None
    
    return config
    

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)s] [%(levelname)s] %(message)s')

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pgoapi").setLevel(logging.WARNING)
    logging.getLogger("rpc_api").setLevel(logging.WARNING)

    config = init_config()
    if not config:
        return
        
    if config.debug:
        log.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    location = config.location
    while True:
        try:
            bot = PokeBot()
            bot.login(config.auth_service, config.username, config.password, config.location)
            bot.start(speedFactor = config.speed)
        except KeyboardInterrupt:
            return
        except:
            posn = bot.api.get_normal_position()
            if posn[0] != 0 and posn[1] != 0:
                location = str(posn[0]) + ", " + str(posn[1])
            log.error("Bot Failed, restarting after 20 sec at {}...".format(location))
            time.sleep(20)

if __name__ == '__main__':
    main()
