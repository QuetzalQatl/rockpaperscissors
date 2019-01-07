from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit, send
from urllib.request import urlopen

#from codenames import game
import time
import random
import traceback
import socket
import sys
import os
import json

#this program needs:
#pip install flask flask-socketio eventlet


PORT=5000 # default, can be set at startup by setting the environment variable 'PORT'
LANIP='192.168.99.100' # default, can be set at startup by setting the environment variable 'LANIP'

#characters allowed in names:
allowed='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-_(){}[]<>!?.,`;:=+-*&^%$#@~ '
maxnamelen=20

localIP='127.0.0.1'
WANIP=''
CLIENTS = {} # dict to track active rooms
CHOICE={}
CHOICE['LEFT']='None'
CHOICE['RIGHT']='None'
STATE={}
STATE['gamestate']='waitingforplayers' # or 'gamerunning' or 'showingwinner'
STATE['goalscore']=3
STATE['rightname']='The Right'
STATE['leftname']='The Left'
STATE['rightwon']=0
STATE['leftwon']=0
STATE['lefthand']='No Connection' # or 'Setup' or 'Rock' or 'Paper' or 'Scissors'
STATE['righthand']='No Connection' # or 'Setup' or 'Rock' or 'Paper' or 'Scissors'
STATE['result']='' # messages to the users

OLDSTATE={}

for key in STATE:
	OLDSTATE[key]=STATE[key]

FlaskSecretKey=os.urandom(512)
		
# initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = FlaskSecretKey
socketio = SocketIO(app)

def checkState():
	changed=False
	for key in STATE:
		if STATE[key]!=OLDSTATE[key]:
			changed=True
			break
	if changed:
		jasonstate= json.dumps(STATE)
		#print (str(jasonstate))
		socketio.emit('stateChanged', (str(jasonstate)), namespace='/rpslobbie')
		for key in STATE:
			OLDSTATE[key]=STATE[key]

def getWideIpAdres():
    try:
        html = urlopen("https://whatsmyip.com/")
        lines=html.readlines()
        html = ''
        for l in lines:
            if l.find(b'Your IP') != -1 and l.find(b'is:') != -1:
                lines2=l.split(b'><')
                for l2 in lines2:
                    if l2.find(b'p class="h1 boldAndShadow">') !=-1 and l2.find(b'</p') !=-1:
                        return l2[27:-3].decode('ascii')
    except:
        traceback.print_exc()
        # perhaps try one or two others
    print ('OMG!!!! Could not find wide ip adres.... Is internet connected/working?')
    return ''

#@socketio.on('message')
#def handle_message(message):
    #print('received message: ' + message)

#@socketio.on('json')
#def handle_json(json):
    #print('received json: ' + str(json))

#@app.route('/favicon.png')
#def favicon():
    #return render_template('favicon.png')

def stripName(name):
	name=name.strip()
	newname=''
	counter=0
	for n in name:
		if n in allowed:
			newname=newname+n
			counter=counter+1
			if counter==maxnamelen:
				break
	return newname
	
def GetConnectTo(remote_address):
    if (remote_address==localIP):
        return localIP+':'+str(PORT)
    elif (remote_address[:4]=='192.'):
        return LANIP+':'+str(PORT)
    else:
        return WANIP+':'+str(PORT)

@app.route('/')
def app_index():
	a= render_template('rps.html')
	a=a.replace('%%CONNECTTO%%',GetConnectTo(request.remote_addr))
	print (request.remote_addr, '/ --> /rps.html')
	print ("request.host="+str(request.host))
	print ("request.user_agent="+str(request.user_agent))
	return a
	
@app.route('/rps')
def app_rps():
    a= render_template('rps.html')
    a=a.replace('%%CONNECTTO%%',GetConnectTo(request.remote_addr))
    print (request.remote_addr, '/rps --> /rps.html')
    return a
	
@socketio.on('Choice', namespace='/rpslobbie')
def on_Choice(side, choice):
	if STATE['gamestate']=='waitingforplayers' or STATE['gamestate']=='gamerunning' or STATE['gamestate']=='showingwinner':
		if (CLIENTS[request.sid]=='LEFT' and side=='Left') or (CLIENTS[request.sid]=='RIGHT' and side=='Right'):
			if choice=='Rock' or choice=='Paper' or choice=='Scissors':
				
				if side=='Left':
					CHOICE['LEFT']=choice
					STATE['lefthand']='Ready'
					if STATE['righthand'] in ['Setup' ,'Rock' ,'Paper' ,'Scissors']:
						STATE['righthand']='Waiting'
						if STATE['gamestate']=='showingwinner':
							STATE['rightwon']=0
							STATE['leftwon']=0
							
				elif side=='Right':
					CHOICE['RIGHT']=choice
					STATE['righthand']='Ready'
					if STATE['lefthand'] in ['Setup' ,'Rock' ,'Paper' ,'Scissors']:
						STATE['lefthand']='Waiting'
						if STATE['gamestate']=='showingwinner':
							STATE['rightwon']=0
							STATE['leftwon']=0
				
				# check both ready
				if STATE['lefthand']=='Ready' and STATE['righthand']=='Ready':
					if STATE['gamestate']=='showingwinner':
						STATE['result']=''
					STATE['gamestate']='gamerunning'
					STATE['lefthand']=CHOICE['LEFT'] 
					STATE['righthand']=CHOICE['RIGHT']
					if CHOICE['RIGHT']=='Rock':
						if CHOICE['LEFT'] =='Scissors':
							STATE['rightwon']=STATE['rightwon']+1
							STATE['result']='Scissors < Rock'
						elif CHOICE['LEFT'] =='Paper':
							STATE['leftwon']=STATE['leftwon']+1
							STATE['result']='Paper > Rock'
						else:
							STATE['result']='Rock = Rock'
					if CHOICE['RIGHT']=='Paper':
						if CHOICE['LEFT'] =='Scissors':
							STATE['leftwon']=STATE['leftwon']+1
							STATE['result']='Scissors > Paper'
						elif CHOICE['LEFT'] =='Rock':
							STATE['rightwon']=STATE['rightwon']+1
							STATE['result']='Rock < Paper'
						else:
							STATE['result']='Paper = Paper'
					if CHOICE['RIGHT']=='Scissors':
						if CHOICE['LEFT'] =='Rock':
							STATE['leftwon']=STATE['leftwon']+1
							STATE['result']='Rock > Scissors'
						elif CHOICE['LEFT'] =='Paper':
							STATE['rightwon']=STATE['rightwon']+1
							STATE['result']='Paper < Scissors'
						else:
							STATE['result']='Scissors = Scissors'
				
				# check for winner			
				if STATE['rightwon']>=STATE['goalscore']:
					STATE['gamestate']='showingwinner'
					STATE['result']=STATE['rightname']+' Wins!!!'
				elif STATE['leftwon']>=STATE['goalscore']:
					STATE['gamestate']='showingwinner'
					STATE['result']=STATE['leftname']+' Wins!!!'
				checkState()
	print (request.sid,side, 'has chosen')
	
@socketio.on('setRightName', namespace='/rpslobbie')
def on_setRightName(name):
	if STATE['gamestate']=='waitingforplayers' or STATE['gamestate']=='showingwinner':
		if CLIENTS[request.sid]=='RIGHT':
			newname=stripName(name)
			if len(newname):
				print (request.sid,'setRightName -->', newname)
				STATE['rightname']=newname
				checkState()
			else:
				print ('ignoring zero length name')
			if len(newname)!=len(name):
				socketio.emit('noGoodName', (request.sid,STATE['rightname'],STATE['leftname']), namespace='/rpslobbie')

@socketio.on('setLeftName', namespace='/rpslobbie')
def on_setLeftName(name):
	if STATE['gamestate']=='waitingforplayers' or STATE['gamestate']=='showingwinner':
		if CLIENTS[request.sid]=='LEFT':
			newname=stripName(name)
			if len(newname):
				print (request.sid,'setLeftName -->', newname)
				STATE['leftname']=newname
				checkState()
			else:
				print ('ignoring zero length name')

@socketio.on('setGoalScore', namespace='/rpslobbie')
def on_setGoalScore(goalscore):
	if STATE['gamestate']=='waitingforplayers' or STATE['gamestate']=='showingwinner':
		if CLIENTS[request.sid]=='RIGHT':
			if len(goalscore):
				print (request.sid,'setGoalScore -->', goalscore)
				try:
					goalscore=abs(int(goalscore))
					if goalscore>0:
						STATE['goalscore']=abs(int(goalscore))
					else:
						socketio.emit('noGoodGoalScore', (request.sid,STATE['goalscore']), namespace='/rpslobbie')
						print (str(goalscore)+' is not a good number')
				except:
					socketio.emit('noGoodGoalScore', (request.sid,STATE['goalscore']), namespace='/rpslobbie')
					print (str(goalscore)+' is not a good number')
				checkState()
			else:
				print ('ignoring zero length goalscore')
			
def getSide():
	needRight=True
	needLeft=True
	for c in CLIENTS:
		if CLIENTS[c]=="RIGHT":
			needRight=False
		elif CLIENTS[c]=="LEFT":
			needLeft=False
	if needRight:
		return "RIGHT"
	elif needLeft:
		return "LEFT"
	else:
		return "OBSERVER"

@socketio.on('requestSide', namespace='/rpslobbie')
def on_requestSide():
    currentSocketId = request.sid
    side=CLIENTS[currentSocketId]
    print('requestSide -->',currentSocketId,side)
    socketio.emit('requestedSide', (currentSocketId,side,json.dumps(STATE)), namespace='/rpslobbie')

@socketio.on('connect', namespace='/rpslobbie')
def on_connect():
	print('Client '+request.sid+' connected')
	currentSocketId = request.sid
	CLIENTS[currentSocketId]=getSide()
	if CLIENTS[currentSocketId]=='RIGHT':
		STATE['righthand']='Setup'
	elif CLIENTS[currentSocketId]=='LEFT':
		STATE['lefthand']='Setup'
	checkState()

@socketio.on('disconnect', namespace='/rpslobbie')
def on_disconnect():
	print('Client '+request.sid+' disconnected')
	currentSocketId = request.sid
	if CLIENTS[currentSocketId]=='RIGHT':
		STATE['righthand']='No Connection'
	elif CLIENTS[currentSocketId]=='LEFT':
		STATE['lefthand']='No Connection'
	CLIENTS.pop(currentSocketId, None)
	checkState()

if __name__ == '__main__':
	try:
		PORT=abs(int(os.getenv('PORT')))
	except:
		pass
	LANIP=os.getenv('LANIP', LANIP)
	WANIP=getWideIpAdres()
	print ()
	print ("Rock Paper Scissors")
	print ("v0.03")
	print ("localIP="+localIP)
	print ("LANIP="+LANIP)
	print ("WANIP="+WANIP)
	print ("PORT="+str(PORT))
	print ()
	socketio.run(app, debug=False, port=PORT, host="0.0.0.0")
