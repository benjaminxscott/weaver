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


# walk dirs to find files as named in config under ./
# XXX if duplicate, don't process and emit warning
	for root,d,f in os.walk("."):
		if conf['filename'] in f:
			location = os.path.join(root,conf['filename'])

# submit to cuckoo 
	multi_part = {'file': open(location, 'rb')}
	rqst = requests.post(cuckoo_url + submit, files=multi_part)
	resp = rqst.json()
	
# store results using cuckoo taskid as index
	samples [resp['task_id']] = conf.copy()
	samples [resp['task_id']]['loc'] = location
	samples [resp['task_id']]['status'] = "pending"

# done with config
infile.close()


# XXX can get md5 from /files/view/id/md5

# XXX refactor to scale based on sample #
timeout = 30
cur = 0
wait_time = 30

# Check if processing has completed for samples
while (cur < timeout ):
	# wait for samples to process
	time.sleep(wait_time)
	cur = cur + wait_time

	for taskid in samples:

		print "DBG checking " + str(taskid)
		print samples[taskid]

		rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
#		print rqst.json()

		# pending, completed, running
		samples[taskid]['status'] = rqst.json()['task']['status']
		print "DBG" + " Task "  + str(taskid) + " is " + samples[taskid]['status'] 

	
# verify cuckoo output
for taskid in samples:

	# check that sample ran and generated report
	rqst = requests.get(cuckoo_url + report + str(taskid))
	if (rqst.status_code != 200):
		samples[taskid]['outcome'] = "sandbox FAILED"
	else:
		report = rqst.json()

		# check JSON for given indicator type for and given indicator
'''
	# TODO location in json for mutex, registry, process, file, network
		print report
		if indicator in report[check]
			samples[taskid]['outcome'] = "report PASSED"
		else:
			samples[taskid]['outcome'] = "report FAILED"
'''

# TODO pretty print summary
for taskid in samples:
	print samples[taskid]
