#!/usr/bin/env python

import socket
import threading
import json
import logging

from libs import cmds_from_file as cff

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(funcName)s %(message)s',datefmt='%H:%M:%S')

def send_flow(m, sock):
    pfeil = '-->'
    src,dst = mac_to_name[m['src']], mac_to_name[m['dst']]
    m2send = json.dumps(m)
    #print(m2send)
    sock.send(m2send)
    if m['direction'] == 'bidirectional':
        m['src'], m['dst'] =  m['dst'], m['src']
        pfeil = '<->'
        m2send = json.dumps(m)
        sock.send(m2send)
    logging.debug("{} {} {} : {}".format(src, pfeil, dst, m['action']))    
    

def send_input(m, sock):
    if not isinstance(m, dict):
        return
    if m['CHANNEL'] == 'setFlow':
        send_flow(m, sock)
    else:
        m = json.dumps(m)
        logging.debug(m)
        sock.send(m)
        

mac_to_name = {}
cur_chan = None
def channel (ch):
  global cur_chan
  cur_chan = ch

# TODO: save current state
#       read connection, logging output
#       read file, create schedule
#       open/close connections based on the schedule

def create_add_mac_msg(task):
  for token in ['cmd', 'port', 'mac', 'node_name']:
    assert token in task
  mac_to_name[task['mac']] = task['node_name']
  return {"CHANNEL":"setMAC2PORT",
	"mac":task['mac'].encode(),
	"port":task['port'], 
	"node_name":task['node_name']}

def create_schedule_msg(task):
  for token in ['cmd', 'src', 'dst', 'schedule']:
    assert token in task
  for dic in task['schedule']:
    yield {"CHANNEL":"setFlow",
	"src":task['src'],
	"dst":task['dst'],
	"direction":task["direction"], 
	"time":dic["time"], 
	"action":dic["action"]}

def main (addr = "127.0.0.1", port = 7790):
  timers = []
  print "Connecting to %s:%i" % (addr,port)
  port = int(port)

  sock = socket.create_connection((addr, port))

  # read infos from file
  schedule = []
  for task in cff.read_tasks_sequentially("./infos/cmds_test.txt"):
    if task['cmd'] == 'add_mac':
      send_input(create_add_mac_msg(task), sock)
    elif task['cmd'] == 'schedule':	
      timers.extend([ threading.Timer(float(x['time']), send_input, [x, sock]) for x in create_schedule_msg(task) ])
  for t in timers:
    #t.daemon = True
    t.start()

  while True:
    try:
      m = raw_input()
      if len(m) == 0: continue
      m = eval(m)
      send_input(m, cur_chan, sock)
          
          
    except EOFError:
      break
    except KeyboardInterrupt:
      break
    except:
      import traceback
      traceback.print_exc()

if __name__ == "__main__":
  import sys
  main(*sys.argv[1:])
else:
  # This will get run if you try to run this as a POX component.
  def launch ():
    from pox.core import core
    log = core.getLogger()
    log.critical("This isn't a POX component.")
    log.critical("Please see the documentation.")
    raise RuntimeError("This isn't a POX component.")
