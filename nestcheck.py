#! /usr/bin/env python
import requests
import sys
import os
import json
import ConfigParser
import time
import argparse

parser = argparse.ArgumentParser ( description = "Test harness for cuckoo. Takes a config file and emits the same filename appended with '.out' with add'l fields for results")
parser.add_argument("--config", help="configuration file for this test", default="sample.cfg")
parser.add_argument("--cuckoo", help="URL where cuckoo API lives (with port number)", default = "http://localhost:8090")
args = parser.parse_args()


# REF cuckoo API endpoints
status = "/cuckoo/status"
taskcheck = "/tasks/view/"
tasklist = "/tasks/list"
submit = "/tasks/create/file"
report = "/tasks/report/"

# check that cuckoo is up
cuckoo_url = args.cuckoo

rqst = requests.get(cuckoo_url + status)
if (rqst.status_code != 200):
    print "ERR: cuckoo is down"
    sys.exit(1)


# load config
config_file = args.config

config = ConfigParser.RawConfigParser()
config.read(config_file)

# find files listed in config 
samples = []
loc = "none"
for sample_name in config.sections():
    for root,d,filename in os.walk("."):
        if sample_name in filename:
            loc = os.path.join(root, sample_name)
    # submit sample to cuckoo 
    multi_part = {'file': open(loc, 'rb')}
    rqst = requests.post(cuckoo_url + submit, files=multi_part)
    resp = rqst.json()

    # save off 
    config.set(sample_name, 'Location', loc)
    config.set(sample_name, 'Task', int(resp['task_id']))
    config.set(sample_name, 'Status', "pending")
    

timeout = 180

# Check each sample
for sample_name in config.sections():
    # TODO consolidate to one for loop() and skip if no file given if "none" in config.get(sample_name, 'Location'):
    # submit one, wait until running, then check
    taskid = config.get(sample_name, 'Task') 

    print "LOG submitted "+  sample_name
    print "LOG waiting "+  timeout + " seconds"
    time.sleep(timeout)

    # update status of sample
    rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
    config.set(sample_name, 'Status', rqst.json()['task']['status']) 

    # check that report exists
    rqst = requests.get(cuckoo_url + report + str(taskid))
    if (rqst.status_code != 200):
        config.set(sample_name, "Outcome", "sandbox FAILED")
        continue # skip to next sample
    
    report = rqst.json()
    
    category = config.get(sample_name, 'Behavior')
    ind = config.get(sample_name, 'Indicator')

    # check for network-based indicators
    if "network" in category:
        try:
            # i.e. if indicator is "http", report[network] has an nonempty list named 'http'
            if ind in report['network']:
                    result =  "report PASSED"
        except KeyError:
            print "ERR invalid config of " + category 
        
    else:
    # check for host indicator
        try:
            # i.e. report[summary][mutexes] contains "evilmutex"
            for item in report['behavior']['summary'][category]:
                if ind in item:
                    result =  "report PASSED"
        except KeyError:
            print "ERR invalid config of " + category 
    
    config.set(sample_name, "Outcome", result)

# done processing, write output file
with open(config_file + ".out", 'wb') as out:
    config.write(out)

