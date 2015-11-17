#!/usr/bin/env python
# author: Prahlad Yeri
# description: DB access class for netpatrol daemon.
import sqlite3
import time
from datetime import datetime
import logging
DB_PATH = "/home/prahlad/source/python/netpatrol/netpatrol.db" #TODO: Change this at the time of installation

class Database:
	def __init__(self, session_id):
		self.conn = sqlite3.connect(DB_PATH)
		self.session_id = session_id
		#cnt = self.conn.cursor().execute("select count(*) from sqlite_master").fetchone()[0]
		#if cnt == 0:
		self.conn.cursor().execute("create table if not exists sessions(id int, iface text, start_time text, end_time text, rx int, tx int, ports_used text)")
		self.conn.cursor().execute("create table if not exists proc_sessions(id int, session_id int, pid int, pname text, rx int, tx int, ports_used text)")
		self.conn.cursor().execute("create table if not exists error_log(id int primary key, log_time int, log_text text)")
		
		## Perform some maintenance, see if any previous unclosed session exists:
		cnt = self.conn.cursor().execute("select count(*) from sessions where end_time is null").fetchone()[0]
		if cnt>0:
			print "found corrupt records"
			self.conn.cursor().execute("delete from sessions where end_time is null") #delete the corrupt record
			self.conn.cursor().execute("insert into error_log(log_time, log_text) values (?,?)",(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Unclosed session found"))
			self.conn.commit()
		self.last_updated = None
			
		## start a new session
		#TODO: This actually happens in start_session
		#cnt = self.conn.cursor().execute("insert into sessions where end_time is null").fetchone()[0]
		#self.conn.cursor().execute("insert into sessions values(?,)").fetchone()[0]
		
		
	def update_proc(self, ppnd):
		for pid in ppnd:
			logging.debug("/proc/" + str(pid) +  "/net/dev=========")
			for iface in ppnd[pid]:
				rx = ppnd[pid][iface]['rx']
				tx = ppnd[pid][iface]['tx']
				if (iface!='lo' and (rx>0 or tx>0)):
					logging.debug(pid, iface, rx, tx)
	
	def end_session(self, d):
		self.conn.cursor().execute("update sessions set end_time=?, rx=?, tx=? where id=? and iface=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), d['pnd']['rx'],d['pnd']['tx'] ,self.session_id, d['name']))
		self.conn.commit()
		self.last_updated = time.time()

	def start_session(self, d):
		self.conn.cursor().execute("insert into sessions values(?,?,?,null,?,?,?)", (self.session_id, d['name'] , datetime.now().strftime("%Y-%m-%d %H:%M:%S"), d['pnd']['rx'],d['pnd']['tx'] ,''))
		self.conn.commit()
		self.last_updated = time.time()
		logging.info("session started")

	def update_session(self, d):
		self.conn.cursor().execute("update sessions set rx=?, tx=? where id=? and iface=?", (d['pnd']['rx'],d['pnd']['tx'] , self.session_id, d['name']))
		self.conn.commit()
		#print iface, rx, tx
		logging.info(str.format("{0}, {1}, {2}, {3}", self.session_id, d['name'], d['pnd']['rx'], d['pnd']['tx']))
		self.last_updated = time.time()
		
		
	#~ def close(self):
		#~ self.conn.cursor().execute("update sessions set end_time=? where id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.session_id))
		
	def update_tcp(self, ppntcp):
		pass
		
		
if __name__ == "__main__":
	db = Database()
