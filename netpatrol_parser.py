import subprocess

def parse_procnetdev():
	command = "cat /proc/net/dev"
	p=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	data = p.communicate()[0]
	return format_data(data,is_pid=False)

def parse_procnetdev_pid():
	command = "tail -n+0 /proc/*/net/dev"
	p=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	data = p.communicate()[0]
	return format_data(data,is_pid=True)

def parse_procnettcp_pid():
	pass
	
#cat /proc/net/dev (!is_pid)
#tail -n+0 /proc/*/net/dev (is_pid)
def format_data(strdata, is_pid=False):
	if is_pid:
		arr = strdata.split("\n\n")
	else:
		arr = [strdata]
		
	presults = {}
	results = {}
	pid = 0
		
	for result in arr: #process each file
		tstr = result.split("\n")
		if is_pid:
			#results = {} #reset results dict 
			sproc = tstr[0].split("/")[2]
			try:
				pid = int(sproc)
			except:
				pass
			
		if (is_pid and pid==0):
			continue #not a valid pid
			
		for line in tstr[1:]: #0,1 & 2 are heading lines in case of is_pid, else just 0,1
			#print line
			if line.find(":") < 0: continue
			pass #start capturing data from here
			iface, data = line.split(":")
			if iface.strip() == 'lo': continue
			iface = iface.strip()
			#results[iface] = data.split()
			arr = data.split()
			if is_pid:
				if not iface in results: results[iface] = {}
				##TODO: get /proc/<pid>/net/cmdline and add it to the process
				cmdline = ''
				try:
					fp = open('/proc/' + str(pid) + '/cmdline','r')
					cmdline = fp.read()
					fp.close()
				except:
					#print 'error occured for cmdline: ' + '/proc/' + str(pid) + '/cmdline'
					pass
				
				if cmdline.strip()=='' or cmdline==None: continue
				cmdline = cmdline.replace(chr(0),'')
				if cmdline.strip()=='' or cmdline==None: continue
				rx = int(arr[0])
				tx = int(arr[8])
				results[iface][pid] = {'cmdline':cmdline, 'rx':rx, 'tx':tx}
				print "done for process ",cmdline, pid, rx, tx
			else:
				results[iface] = {'rx':int(arr[0]), 'tx':int(arr[8])}
		#if is_pid: presults[pid] = results
		#print "processed for ", pid
	if is_pid:
		#return presults
		return results
	else:
		return results

### See http://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-u		
#~ for line in lines[2:]:
    #~ if line.find(":") < 0: continue
    #~ face, data = line.split(":")
    #~ faceData = dict(zip(cols, data.split()))
    #~ faces[face] = faceData
