# PokeBot
A Pokemon Go bot app based on python
that can do following things:

1. Walk as you & starts at any location
2. Catch Pokemons
3. Search PokeStops
4. Drop lower cp pokemons
5. Throw away items
6. Adjustable speed 

## Desktop App
![ScreenShot](https://raw.githubusercontent.com/lkzhao/PokeBot/master/releases/PokeBot.png)
[Download Link(Mac)](https://raw.githubusercontent.com/lkzhao/PokeBot/master/releases/PokeBot.zip)

This is in development! There is no crash handling logic. so not as stable as the command line one.


## Installation (Command Line Version)
1. first install python and pip
```
sudo pip install virtualenv
mkdir ENV
virtualenv ENV
source ENV/bin/activate
pip install --upgrade -r requirements.txt
```

## Usage
```
src/pokebot.py -u <EMAIL> -p <PASSWORD> -a <SIGNINTYPE> -l <LOCATION> -s <SPEED>
```
* SIGNINTYPE: google or ptc
* LOCATION: any location that google maps understands. can be LATITUDE, LONGITUDE
* SPEED: any integer >= 1, (1 is normal human speed, 10 is recommanded, 20+ will be banned)

## Compile Desktop App (Mac)
```bash
cd app
npm install
sudo npm install electron-packager -g
sudo npm install electron-prebuilt -g

# compile python executable
pip install pyinstaller
pyinstaller main.spec --clean --distpath app
# compile app
electron-packager app --platform=darwin --arch=x64
```

## Credits
[tejado](https://github.com/tejado/pgoapi) Awesome pgoapi framework
