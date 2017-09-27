# placed.py

simple /r/place implement using flask

## acknowledgement

this project uses

* flask
* Flask-Sockets
* pyredis
* pyotp

to build backend

using hi-base32 to make demo page

## prepare

### install requirements

    pip install -r requirements.txt
    echo (build your redis, then)
    /path/to/redis-server

### create your extern auth

implement ext_auth(uid:int, token:bytes(24)):bool at externauth.py like externauth.py.example

## run

    python main.py run

## create canvas

    curl -d "level=<the phc level you want:integer>" localhost:5000/somecanvasid

## demo page

at /statictest/<canvasid>.html

## dump history

    python main.py dumph

## license

    MIT license
