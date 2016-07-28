#!/usr/bin/env python
from time import sleep
import sys, os, logging
from flask import Flask, request, send_from_directory, render_template
from flask import jsonify
from pokebot import *
import json

from POGOProtos.Enums_pb2 import PokemonId
from POGOProtos.Inventory_pb2 import ItemId

# determine if application is a script file or frozen exe
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"app")
print(application_path)
os.chdir(application_path)

app = Flask(__name__, static_url_path='/static', static_folder=os.path.join(application_path, "static"))
bot = PokeBot()

@app.route("/login", methods=['POST', 'GET'])
def login():
  global bot
  if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'location' in request.form:
    bot.stop()
    bot = PokeBot()
    if bot.login("google", str(request.form['username']), str(request.form['password']), str(request.form['location'])):
      bot.start(True, 10)
      return "ok"
  return "ok" if bot.running() else "error"

@app.route("/updates")
def updates():
  (x,y,z) = bot.api.get_normal_position()
  rtn = json.dumps({
    "position": {"lat":x, "lng":y}, 
    "forts":bot.forts, 
    "actions":bot.actions,
    "inventory":[{"id":x, "name":ItemId.Name(x), "count":y} for x, y in bot.inventory.iteritems()],
    "pokemons":[{"id":x, "name":PokemonId.Name(x), "data":y} for x, y in bot.pokemons.iteritems()]
    }).replace("NaN", "null")
  bot.actions = []
  return rtn

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return app.send_static_file('index.html')

if __name__ == "__main__":
  logging.basicConfig(level=logging.WARNING)
  logging.getLogger("lukeapi").setLevel(logging.INFO)
  app.run()
  bot.stop()
