#! /usr/bin/env python
import requests
import sys
import os
import time
import argparse
import hashlib

# XXX turn into functions

parser = argparse.ArgumentParser ( description = "Test harness for cuckoo")
parser.add_argument("--config", help="configuration file for this test")
parser.add_argument("--cuckoo", help="URL where cuckoo API lives (with port")
args = parser.parse_args()

if (args.cuckoo == None):
	cuckoo_url = "http://localhost:8090"
else:
	config_file = args.cuckoo


# cuckoo API endpoints
status = "/cuckoo/status"
taskcheck = "/tasks/view/"
tasklist = "/tasks/list"
submit = "/tasks/create/file"

# check that cuckoo is up
rqst = requests.get(cuckoo_url + status)
if (rqst.status_code != 200):
	print "ERR: cuckoo is down"
	print "fix it and re-run"
	sys.exit(1)

# load config
if (args.config == None):
	config_file = "./cfg.in"
else:
	config_file = args.config

infile = open(config_file)

samples = {}

# parse config 
for line in infile:
	# ignore comments
	if (line[0] == '#'):
		continue

	# remove newline
	line = line.rstrip()

	conf = dict (thing.split("=") for thing in line.split("|"))
	#print "DBG: " + str(conf)

# TODO save family, check / indicator

# XXX if duplicate, don't process and emit warning

# walk dirs to find files as named in config under ./
	for root,d,f in os.walk("."):
		if conf['filename'] in f:
			location = os.path.join(root,conf['filename'])
			print "DBG" + location

# generate md5 of binary
	binary = open (location, "rb")
	md5sum = hashlib.md5(binary.read()).hexdigest()
	binary.close()

# submit to cuckoo 
	multi_part = {'file': open(location, 'rb')}
	rqst = requests.post(cuckoo_url + submit, files=multi_part)
	resp = rqst.json()
	
# save off to dict with taskid as index
	samples [resp['task_id']]= {'md5': md5sum, 'filename': conf['filename'], 'loc':location}


# done with config
infile.close()


# hit cuckoo API to see if sample is complete

# XXX may need to be higher timeout
timeout = 60
cur = 0
wait_time = 10

while (cur < timeout ):
	for taskid in samples:
		print "DBG checking " + str(taskid)
		print samples[taskid]

		rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
		
		print rqst.json()
		print rqst.json()['task']['status']
		if not rqst.json()['task']['completed_on']: 
			print "not done yet"

	# spin for a bit
	time.sleep(wait_time)
	cur = cur + wait_time
	print cur
	
# TODO search JSON for given indicator type (host, network) and given indicator (reg, http, tcp, udp, etc)

