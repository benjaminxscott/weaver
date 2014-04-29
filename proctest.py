#! /usr/bin/env python
import requests
import sys
import os
import time
import argparse

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
report = "/tasks/report/"

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

# submit to cuckoo 
	multi_part = {'file': open(location, 'rb')}
	rqst = requests.post(cuckoo_url + submit, files=multi_part)
	resp = rqst.json()
	
# save off to dict with taskid as index
	samples [resp['task_id']]= {'filename': conf['filename'], 'loc':location, 'status': "pending"}


# done with config
infile.close()


# XXX can get md5 from /files/view/id/md5

# hit cuckoo API to see if sample is complete

# XXX may need to be higher timeout
timeout = 60
cur = 0
wait_time = 10

while (cur < timeout ):
	for taskid in samples:
		# skip to next if we know this task is done
		if "completed" in samples[taskid]['status'] :
			continue

		print "DBG checking " + str(taskid)
		print samples[taskid]

		rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
		print rqst.json()

		# pending, completed, running, reported
		samples[taskid]['status'] = rqst.json()['task']['status']

	# spin for a bit
	time.sleep(wait_time)
	cur = cur + wait_time
	print cur
	
# TODO search JSON for given indicator type (host, network) and given indicator (reg, http, tcp, udp, etc)

# rqst = requests.get(cuckoo_url + report + str(taskid))
# parse out json for network / host as needed
# 404 if not there
