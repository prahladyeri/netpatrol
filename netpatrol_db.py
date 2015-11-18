#!/usr/bin/env python
# author: Prahlad Yeri
# description: DB access class for netpatrol daemon.
import sqlite3
import time
from datetime import datetime, timedelta
import logging
DB_PATH = "/home/prahlad/source/python/netpatrol/netpatrol.db" #TODO: Change this at the time of installation

class Database:
	def __init__(self, session_id):
		self.conn = sqlite3.connect(DB_PATH)
		self.conn.row_factory = sqlite3.Row
		self.session_id = session_id
		#cnt = self.conn.cursor().execute("select count(*) from sqlite_master").fetchone()[0]
		#SESSION_ID + IFACE MAKE A PRIMARY KEY
		self.conn.cursor().execute("create table if not exists sessions(id int, iface text, start_time text, end_time text, rx int, tx int, ports_used text)")
		self.conn.cursor().execute("create table if not exists sessions_p(session_id int, iface text, pid int, pname text, cmdline text, rx int, tx int, ports_used text)")
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

	def get_hist(self, period):
		if period == 'D': #last day
			fdate = datetime.now().strftime("%Y-%m-%d 00:00:00.000")
		if period == '1M': #last month
			fdate = datetime.now().strftime("%Y-%m-01 00:00:00.000")
		if period == '6M':
			fdate = (datetime.now() - timedelta(weeks=24)).strftime("%Y-%m-01 00:00:00.000")
		if period == '3M':
			fdate = (datetime.now() - timedelta(weeks=12)).strftime("%Y-%m-01 00:00:00.000")
			
		tdate = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
		tsql = 'select iface, sum(rx) as rxbytes, sum(tx) as txbytes from sessions where start_time>=? and end_time<=? group by iface'
		result = self.conn.cursor().execute(tsql, (fdate, tdate)).fetchall()
		retval = []
		#print result[0], result[1]
		#print tsql, fdate, tdate
		for session in result:
			#print session['iface'], session['rxbytes'], session['txbytes']
			#if session['rxbytes'] ==0 and session['txbytes'] ==0: continue
			retval.append({'iface':session['iface'], 'rxbytes':session['rxbytes'], 'txbytes':session['txbytes']})
		return retval
	
	def get_hist_p(self, period):
		pass
		
	def get_active_p(self):
		pass

	
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
		
		#self.conn.commit()
		#print iface, rx, tx
		logging.info(str.format("{0}, {1}, {2}, {3}", self.session_id, d['name'], d['pnd']['rx'], d['pnd']['tx']))
		self.last_updated = time.time()
		
	def update_session_p(self, d, pid):
		#now lets do the same for processes
		#(session_id int, iface text, pid int, pname text, cmdline text, rx int, tx int, ports_used text)
		iface = d['name']
		cmdline=''
		try:
			cmdline = d['ppnd'][pid]['cmdline']
		except:
			print 'ERROR', d['ppnd'][pid],  d['ppnd']
		rx = d['ppnd'][pid]['rx']
		tx = d['ppnd'][pid]['tx']
		if rx>0 or tx>0:
			self.conn.cursor().execute("delete from sessions_p where session_id=? and iface=? and pid=?", (self.session_id, iface, pid))
			self.conn.cursor().execute("insert into sessions_p values(?,?,?,?,?,?,?,'')", (self.session_id, iface, pid ,cmdline, cmdline, rx,tx))
		
		#self.conn.commit()
		#print iface, rx, tx
		#logging.info(str.format("{0}, {1}, {2}, {3}", self.session_id, d['name'], d['pnd']['rx'], d['pnd']['tx']))
		self.last_updated = time.time()
		
	#~ def close(self):
		#~ self.conn.cursor().execute("update sessions set end_time=? where id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.session_id))
		
	def update_tcp(self, ppntcp):
		pass
		
		
if __name__ == "__main__":
	db = Database()

	
	#~ def update_proc(self, ppnd):
		#~ for pid in ppnd:
			#~ logging.debug("/proc/" + str(pid) +  "/net/dev=========")
			#~ for iface in ppnd[pid]:
				#~ rx = ppnd[pid][iface]['rx']
				#~ tx = ppnd[pid][iface]['tx']
				#~ if (iface!='lo' and (rx>0 or tx>0)):
					#~ logging.debug(pid, iface, rx, tx)
