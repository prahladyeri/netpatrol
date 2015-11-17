#!/usr/bin/env python
# author: Prahlad Yeri
# description: The netpatrol userspace daemon. A small program to track bandwidth consumption and put in database.
# http://askubuntu.com/a/409426/49938
# find all icon indicator names in /usr/share/icon/* folders on ubuntu 14.04

import sys, time, logging
import threading
import random, subprocess
from gi.repository import GLib, Gtk, GObject
from gi.repository import AppIndicator3 as appindicator
#import dbus.mainloop.glib; dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
#import NetworkManager
import netpatrol_parser
from netpatrol_db import Database

__version__ = "1.1.5"

class MyIndicator:
	def __init__(self, root):
		self.app = root
		self.ind = appindicator.Indicator.new(
								self.app.name,
								#"indicator-messages",
								"view-ringschart-symbolic",
								#"ubuntuone-music",
								#"avatar-default",
								#~ "network-server-symbolic",
								#~ "network-cellular-4g-symbolic",
								#~ "network-cellular-connected-symbolic",
								#~ "network-wired-symbolic",
								# "ubuntuone-client-idle.svg",
								#~ "network-idle-symbolic",
								#~ "network-server",
								#~ "network-workgroup",
								#~ "network-idle-symbolic",
								appindicator.IndicatorCategory.APPLICATION_STATUS)
		self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)
		self.menu = Gtk.Menu()
		item = Gtk.MenuItem()
		item.set_label("Net Patrol")
		item.connect("activate", self.app.main_win.cb_show, '')
		self.menu.append(item)

		#~ item = Gtk.MenuItem()
		#~ item.set_label("Configuration")
		#~ item.connect("activate", self.app.conf_win.cb_show, '')
		#~ self.menu.append(item)
		
		self.menu.append(Gtk.SeparatorMenuItem())
		
		item = Gtk.MenuItem()
		item.set_label("About")
		#item.connect("activate", self.app.about_win.cb_show, '')
		item.connect("activate", self.app.show_about_dialog)
		self.menu.append(item)
		
		self.menu.append(Gtk.SeparatorMenuItem())

		item = Gtk.MenuItem()
		item.set_label("Exit")
		item.connect("activate", self.cb_exit, '')
		self.menu.append(item)

		self.menu.show_all()
		self.ind.set_menu(self.menu)

	def cb_exit(self, w, data):
		 Gtk.main_quit()
		 
class MyMainWin(Gtk.Window):
	def __init__(self, root):
		Gtk.Window.__init__(self,default_height=300, default_width=600, title="Active Connections")
		self.app = root
		self.m_period = "1M"
		self.connect("delete-event", self.cb_delete) ##TODO: switch this
		## self.connect("delete-event", Gtk.main_quit)
		
	def on_combo_changed(self, combo):
		tree_iter = combo.get_active_iter()
		if tree_iter != None:
			model = combo.get_model()
			data = model[tree_iter][1]
			self.m_period = data
			print("Selected: data=%s" % self.m_period)

	def cb_show(self, w, data):
		#self.vbox = Gtk.VBox()
		#self.vbox.set_border_width(0)
		## self.progress = Gtk.ProgressBar()
		#self.vbox.pack_start(self.progress, True, True, 0)
		## self.progress.set_fraction(0.50)
		#self.vbox.add(self.progress)
		#self.main_win.add(self.vbox)
		## self.add(self.progress)
		
		## Create the data-models first
		self.rs_period = Gtk.ListStore(str, str)
		self.rs_period.append(['Last Month', '1M'])
		self.rs_period.append(['Last Quarter', '3M'])
		self.rs_period.append(['Last Six Months', '6M'])
		self.rs_period.append(['Last 24 hrs', 'D'])
		
		self.rs_stats = Gtk.ListStore(str, str, str)
		self.rs_stats.append(["ppp0", "50.0mb", "3mb"])
		self.rs_stats.append(["eth0", "76.5mb", "3mb"])
		self.rs_stats.append(["bnt0", "50.1mb", "3mb"])
		
		self.rs_pstats = Gtk.ListStore(str, str, str, str)
		self.rs_pstats.append(["ppp0", "firefox", "1024.0mb", "3mb"])
		self.rs_pstats.append(["ppp0", "transmission", "7.5mb", "3mb"])
		self.rs_pstats.append(["ppp0", "rhythm-box", "5.1mb", "3mb"])
		
		self.rs_process = Gtk.ListStore(str, str, str, str, str)
		self.rs_process.append(["ppp0", "firefox", "tcp:80", "50.0mb", "3mb"])
		self.rs_process.append(["ppp0", "dnsmasq", "tcp:50", "76.5mb", "3mb"])
		self.rs_process.append(["ppp0", "transmission", "tcp:20", "50.1mb", "3mb"])

		## Now work on the actual controls
		self.notebook = Gtk.Notebook()
		self.add(self.notebook)
		
		#Stats Page
		self.page1 = Gtk.Box()
		self.page1.set_border_width(5)
		vbox = Gtk.VBox()
		## Add a combo box
		#cmb_period = Gtk.ComboBox.new_with_model_and_entry(self.rs_period)
		cmb_period = Gtk.ComboBox.new_with_model(self.rs_period)
		cmb_period.connect("changed", self.on_combo_changed)
		#cmb_period.set_entry_text_column(0)
		renderer_text = Gtk.CellRendererText()
		cmb_period.pack_start(renderer_text, True)
		cmb_period.add_attribute(renderer_text,"text",0)
		cmb_period.set_active(0)
		
		## Add treeview for summary
		tvw_stats = Gtk.TreeView(model=self.rs_stats)
		column_text = Gtk.TreeViewColumn("interface", Gtk.CellRendererText(), text=0)
		tvw_stats.append_column(column_text)
		column_text = Gtk.TreeViewColumn("RX Bytes", Gtk.CellRendererText(), text=1)
		tvw_stats.append_column(column_text)
		column_text = Gtk.TreeViewColumn("TX Bytes", Gtk.CellRendererText(), text=2)
		tvw_stats.append_column(column_text)
		#box.pack_start(tvw_stats, True, True, 0)
		#NOTE TO SELF: use page.pack_start instead of page.add() if you need expand/fill control on widgets.
		#self.page1.add(box)
		
		## Add treeview for process
		tvw_pstats = Gtk.TreeView(model=self.rs_pstats)
		column_text = Gtk.TreeViewColumn("interface", Gtk.CellRendererText(), text=0)
		tvw_pstats.append_column(column_text)
		column_text = Gtk.TreeViewColumn("process", Gtk.CellRendererText(), text=1)
		tvw_pstats.append_column(column_text)
		column_text = Gtk.TreeViewColumn("RX Bytes", Gtk.CellRendererText(), text=2)
		tvw_pstats.append_column(column_text)
		column_text = Gtk.TreeViewColumn("TX Bytes", Gtk.CellRendererText(), text=3)
		tvw_pstats.append_column(column_text)
		
		## Pack all controls
		vbox.pack_start(cmb_period, False, False, 0)
		vbox.pack_start(tvw_stats, False, True, 0)
		vbox.pack_start(tvw_pstats, True, True, 0)
		self.page1.pack_start(vbox, True, True, 0)
		self.notebook.append_page(self.page1, Gtk.Label('Bandwidth Stats'))
		#Process page
		self.page2 = Gtk.Box()
		self.page2.set_border_width(5)
		treeview = Gtk.TreeView(model=self.rs_process)
		column_text = Gtk.TreeViewColumn("Process", Gtk.CellRendererText(), text=0)
		treeview.append_column(column_text)
		column_text = Gtk.TreeViewColumn("Protocols", Gtk.CellRendererText(), text=1)
		treeview.append_column(column_text)
		column_text = Gtk.TreeViewColumn("RX Bytes", Gtk.CellRendererText(), text=2)
		treeview.append_column(column_text)
		column_text = Gtk.TreeViewColumn("TX Bytes", Gtk.CellRendererText(), text=3)
		treeview.append_column(column_text)
		self.page2.pack_start(treeview, True, True, 0)
		self.notebook.append_page(self.page2, Gtk.Label("Active Processes"))
		
		#renderer_editabletext = Gtk.CellRendererText()
		#renderer_editabletext.set_property("editable", True)
		#column_editabletext = Gtk.TreeViewColumn("Editable Text", renderer_editabletext, text=1)
		#treeview.append_column(column_editabletext)
		#renderer_editabletext.connect("edited", self.text_edited)
		#self.add(treeview)		
		self.show_all()
	
	def cb_delete(self, w, data):
		logging.debug( "delete event")
		
class MyApp(Gtk.Application):
	def __init__(self, app_name):
		Gtk.Application.__init__(self)
		self.db = None
		self.active_session_id = 0
		self.active_sessions = None
		self.active_processes = None
		self.name = app_name
		self.main_win = MyMainWin(self)
		self.main_win.set_position(Gtk.WindowPosition.CENTER)
		#self.main_win.connect("delete-event", redraw) #self.main_win.hide_on_delete
		
		#~ self.conf_win = MyConfigWin(self)
		#~ self.conf_win.set_position(Gtk.WindowPosition.CENTER)
		#self.conf_win.connect("delete-event", redraw) #self.main_win.hide_on_delete
		
		#self.about_win  = MyAboutWin(self)
		#self.about_win.set_position(Gtk.WindowPosition.CENTER)
		
		
		self.indicator = MyIndicator(self)
		
        #handler=Handler()
        #builder.connect_signals(handler)
        #w_main.resize(600,300)
        #wmain.show()
        

	def show_about_dialog(self, arg1):
		global about_win
		if not 'about_win' in globals(): about_win = None
		if about_win != None: return #old dialog is still running
		builder = Gtk.Builder()
		builder.add_from_file('netpatrol.glade')
		about_win = builder.get_object('win_about')
		about_win.set_version(__version__)
		about_win.app = self
		response = about_win.run()
		#if response == Gtk.RESPONSE_DELETE_EVENT or response == Gtk.RESPONSE_CANCEL:
		if response == Gtk.ResponseType.OK or response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
			about_win.close()
			about_win = None
			logging.info('about dialog destroyed')
		else:
			logging.info(response)
			#self.wTree.get_widget("aboutdialog1").hide()
			
	def show_basic_stats():
		pass
		
	## Added for multi-threading
	def update_progess(self, i):
		#It is easier to ask for forgiveness, than permission!
		#~ try:
			#~ self.main_win.progress.pulse()
			#~ self.main_win.progress.set_text("idle_" + str(i))
			#~ #print 'success'
		#~ except AttributeError:
			#~ #print "Method does not exist"
			#~ pass
		#~ if self.main_win.active: self.main_win.liststore[0][2] = str(round(random.random(), 2))
		
		#. Open local database and do any needed one-time maintenance in constructor (singleton pattern).
		#~ if self.db == None:
			#~ self.db = Database()
		gui_page = self.main_win.notebook.get_current_page()
		#. PARSE /proc/net/dev
		pnd = netpatrol_parser.parse_procnetdev()
		logging.debug("/proc/net/dev=========")
		for iface in pnd:
			#if iface!='lo': print iface, pnd[iface][0], pnd[iface][8]
			pass
		logging.debug( "")
		
		#. PARSE /proc/<pid>/net/dev
		ppnd = netpatrol_parser.parse_procnetdev_pid()
		#~ print ppnd
		for pid in ppnd:
			#print "/proc/" + str(pid) +  "/net/dev========="
			for iface in ppnd[pid]:
				rx = int(ppnd[pid][iface]['rx'])
				tx = int(ppnd[pid][iface]['tx'])
				if (iface!='lo' and (rx>0 or tx>0)): logging.debug(str.format("{0} {1} {2}", iface, rx, tx))
		
		#. PARSE /proc/<pid>/net/tcp
		ppntcp = netpatrol_parser.parse_procnettcp_pid()

		#. START DOING SOME WORK
		if self.active_sessions == None:
			# START A NEW SESSION
			self.active_sessions = {}
			self.active_processes = {}
			self.active_session_id = int(time.time()) #Generate a random new session_id which should be pretty long.
			self.db = Database(self.active_session_id)
			logging.info("New db created")
			
		added = set(pnd.keys()).difference(self.active_sessions.keys()) #newly added iface in pnd
		removed = set(self.active_sessions.keys()).difference(pnd.keys()) #just removed iface from pnd
		#no change
		inters = set(self.active_sessions.keys()).intersection(pnd.keys())

		if len(added)>0:
			logging.info('ADDED')
			logging.info(added)
		if len(removed)>0:
			logging.info('REMOVED')
			logging.info(removed)
		#~ if len(inters)>0:
			#~ logging.info('INTERSECTION')
			#~ logging.info(len(inters))
		
		#. Check our self.active_sessions and compare with pnd.
		#. if new iface found in pnd, add it to active_sessions and give it a start_time.
		for iface in added:
			self.active_sessions[iface] = {}
			self.active_sessions[iface]['name'] = iface
			self.active_sessions[iface]['pnd'] = pnd[iface]
			self.active_sessions[iface]['start_time']  = time.time() #TODO: This is only for ref, actually set by db class
			self.active_sessions[iface]['end_time']  = 0
			self.db.start_session(self.active_sessions[iface])
			
		#. else if iface exists in active_sessions but not in pnd, it means session is ended, so update end_time and remove from db and then dict.
		for iface in removed:
			#active_sessions[iface]['data'] = pnd[iface]
			self.active_sessions[iface]['end_time']  = time.time()
			self.db.end_session( self.active_sessions.pop(iface))
			
		
		#. For each existing iface in active_sessions, update its rx and tx values.
		for iface in inters:
			self.active_sessions[iface]['pnd']  = pnd[iface]
			#update db if needed
			last_updated = self.db.last_updated
			if last_updated==None or (time.time() - last_updated)>10: #update after interval of a few secs
				self.db.update_session(self.active_sessions[iface])
				logging.info("updated session")
		
		#. if main_win is active, update the gui too.
		if gui_tab==0: #basic stats
			self.db.get_history('1M')
			self.db.get_history_p('1M')
		elif gui_tab==1: #active processes
			pass
		return
	
	def daemon_thread(self):
		while True:
		#for i in range(1):
			#TODO:
			#. Spare thread. Make use of this thread in case it is needed.
			GLib.idle_add(self.update_progess, 0)
			time.sleep(0.2)

		
	def close_all_sessions(self):
		for iface in self.active_sessions.keys():
			self.db.end_session(self.active_sessions[iface])
		
	def run(self):
		thread = threading.Thread(target=self.daemon_thread)
		thread.daemon = True
		thread.start()
		## GLADE experiment
		#~ builder=Gtk.Builder()
		#~ builder.add_from_file('nsgui.glade')
		#~ w_main=builder.get_object('win_main')
		#frmConfigure=builder.get_object('frmConfigure')
		#handler=Handler()
		#builder.connect_signals(handler)
		#~ w_main.resize(600,300)
		#~ w_main.show()
		#~ Gtk.main()
		#~ return

		self.main_win.cb_show(None, None)
		Gtk.main()
		#self.db.close() #TODO: Ensure that our thread is closed when it reaches here.
		self.close_all_sessions()
		logging.info("database closed.")
		logging.info("Have a Good Day!")
		
#~ def display_sig(*args, **kwargs):
def run():
	#~ print("Received signal: %s.%s" % (kwargs['d_interface'], kwargs['d_member']))
	#~ print("Sender:          (%s)%s" % (kwargs['d_sender'], kwargs['d_path']))
	#~ print("Arguments:       (%s)" % ", ".join([str(x) for x in args]))
	#~ print("-------------------")
	#~ fp = open('/proc/net/dev','r')
	#~ proc_net_dev = fp.read()
	#~ fp.close()
	#~ print("proc_net_dev:\n")
	#~ print(proc_net_dev)

	# Calling GObject.threads_init() is not needed for PyGObject 3.10.2+
	#GObject.threads_init()
	#~ d_args = ('sender', 'destination', 'interface', 'member', 'path')
	#~ d_args = dict([(x + '_keyword', 'd_' + x) for x in d_args])
	#~ NetworkManager.NetworkManager.connect_to_signal('CheckPermissions', display_sig, **d_args)
	#~ NetworkManager.NetworkManager.connect_to_signal('StateChanged', display_sig, **d_args)
	#~ NetworkManager.NetworkManager.connect_to_signal('PropertiesChanged', display_sig, **d_args)
	#~ NetworkManager.NetworkManager.connect_to_signal('DeviceAdded', display_sig, **d_args)
	#~ NetworkManager.NetworkManager.connect_to_signal('DeviceRemoved', display_sig, **d_args)
	#~ 
	#~ print("Subscribed to NetworkManager events. Waiting for signals")
	#~ print("-------------------")
	
	logging.basicConfig(stream=sys.stderr, level=logging.INFO)	
	app = MyApp('Netstat GUI')
	app.run()
	sys.exit(0)

if __name__ == '__main__':
	run()
