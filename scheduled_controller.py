from pox.core import core
from pox.messenger import *
import pox.openflow.libopenflow_01 as of
from collections import namedtuple
from pox.lib.addresses import EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet


log = core.getLogger()
switch = None
curr_flows = {}

class setFlowService (object):
  def __init__ (self, parent, con, event):
    self.con = con
    self.parent = parent	# setFlowBot
    self.listeners = con.addListeners(self)

    # We only just added the listener, so dispatch the first message manually.
    self._handle_MessageReceived(event, event.msg)

  def _handle_ConnectionClosed (self, event):
    self.con.removeListeners(self.listeners)
    self.parent.clients.pop(self.con, None)

  def _handle_MessageReceived (self, event, msg):
    if msg['CHANNEL'] != 'setFlow':
        return
    global switch
    log.debug("setFlowService received {}".format(msg))
    src, dst, action = EthAddr(msg.get('src')), EthAddr(msg.get('dst')), msg.get('action')
    self.con.send(reply(msg, msg = "received {}".format(msg)))
    if switch is not None:
        switch.set_flow(src, dst, action)
    else:
        log.debug("Switch not started, ignoring command")
        assert False

class setFlowBot (ChannelBot):
  def _init (self, extra):
    self.clients = {}

  def _unhandled (self, event):
    connection = event.con
    if connection not in self.clients:
      self.clients[connection] = setFlowService(self, connection, event)


class setMAC2PORTService (object):
  def __init__ (self, parent, con, event):
    self.con = con
    self.parent = parent	# setMACsBot
    self.listeners = con.addListeners(self)

    self._handle_MessageReceived(event, event.msg)

  def _handle_ConnectionClosed (self, event):
    self.con.removeListeners(self.listeners)
    self.parent.clients.pop(self.con, None)

  def _handle_MessageReceived (self, event, msg):
    if msg['CHANNEL'] != 'setMAC2PORT':
        return
    global switch
    log.debug("setMAC2PORTService received {}".format(msg))
    mac = EthAddr(msg.get('mac'))
    port = int(msg.get('port'))
    node_name = msg.get('node_name')
    ip = msg.get('ip')

    if switch is not None:
        switch.mac_to_port[mac] = port
        switch.ip_to_mac[ip] = mac
        #switch.node_infos.add({'mac':mac, 'port':port, 'node_name':node_name, 'ip':ip})
        #import pdb; pdb.set_trace()
    else:
        log.debug("Switch not started, ignoring command")
        assert False

class setMACsBot (ChannelBot):
  def _init (self, extra):
    self.clients = {}

  def _unhandled (self, event):
    connection = event.con
    if connection not in self.clients:
      self.clients[connection] = setMAC2PORTService(self, connection, event)

class MessengerExample (object):
  def __init__ (self):
    core.listen_to_dependencies(self)

  def _all_dependencies_met (self):
    setFlowBot(core.MessengerNexus.get_channel("setFlow"))
    setMACsBot(core.MessengerNexus.get_channel("setMAC2PORT"))

class DTN_Controller(object):
  def __init__ (self, connection):
    global switch
    global curr_flows
    self.connection = connection
    self.conn_key = namedtuple("conn_key", ["src", "dst"])
    switch = self

    # This binds our PacketIn event listener
    connection.addListeners(self)

    self.mac_to_port = {}
    self.ip_to_mac = {}
    self.node_infos = set()

  def resend_packet (self, packet_in, out_port):
    msg = of.ofp_packet_out()
    msg.data = packet_in

    # Add an action to send to the specified port
    action = of.ofp_action_output(port = out_port)
    msg.actions.append(action)

    # Send message to switch
    self.connection.send(msg)

  # src,dst: mac addresses
  # action: FORWARD/DROP
  def set_flow(self, mac_src, mac_dst, action):
    
    key = self.conn_key(src=mac_src, dst=mac_dst)

    # if there is a flow, we must flip it
    curr_flows[key] = { "forward": True if action=="forward" else False }
    msg = of.ofp_flow_mod()
    match = of.ofp_match(dl_src = mac_src, dl_dst = mac_dst)
    msg.match = match
    if curr_flows[key]['forward'] == True:
        assert(mac_dst in self.mac_to_port)
        action = of.ofp_action_output(port = self.mac_to_port[mac_dst])
        msg.actions.append(action)
    else: # remove flow if existent
        msg.command=of.OFPFC_DELETE
        msg.flags = of.OFPFF_SEND_FLOW_REM 
    
    log.debug("Set key forwarding in key {} to {}".format(key, curr_flows[key]['forward']))
    self.connection.send(msg)
        
  def _handle_PacketIn (self, event):
      log.debug("Dropping packet")

def launch ():
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    DTN_Controller(event.connection)
   
  core.openflow.addListenerByName("ConnectionUp", start_switch)
  MessengerExample()
