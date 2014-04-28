#! /usr/bin/env python
import requests
import sys
import os
import argparse
import hashlib


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

print "DBG: " + str(infile)

# parse config 
for line in infile:
	# ignore comments
	if (line[0] == '#'):
		continue

	# remove newline
	line = line.rstrip()

	conf = dict (thing.split("=") for thing in line.split("|"))
	#print "DBG: " + str(conf)

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
	print "DBG" + md5sum

# submit to cuckoo 
	multi_part = {'file': open(location, 'rb')}
	rqst = requests.post(cuckoo_url + submit, files=multi_part)
	print "DBG" + rqst.json()['task_id']
	
# TODO emit log w/ processing ID, MD5, filename, malware fam

# TODO wait for sample to be complete, hit cuckoo API
	rqst = requests.get(cuckoo_url + status)
	print rqst.text
	

# TODO search JSON for given indicator type (host, network) and given indicator (reg, http, tcp, udp, etc)

infile.close()
