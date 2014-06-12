#! /usr/bin/env python
import requests
import sys
import os
import json
import ConfigParser
import time
import argparse

parser = argparse.ArgumentParser ( formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description = "Automatic submission suite for cuckoobox, meant for testing / verification of sandbox images. \n"
            + "Takes a configuration file listing the sample name and success criteria")
parser.add_argument("--config", help="configuration file", default="sample.cfg") 
parser.add_argument("--cuckoo", help="URL and port for cuckoo server API", default="http://localhost:8090") 
parser.add_argument("-v","--verbose", help="have verbose output", action='store_true') 


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
try:
    config.read(config_file)
except:
    print "ERR: Configuration file did not exist: " + config_file
    exit(1)

# Submit each sample and wait for results

for sample_name in config.sections():

    # try to find sample under current dir
    for root,d,filename in os.walk("."):
        if sample_name in filename:
            try:
                loc = os.path.join(root, sample_name)
            except NameError:
                loc = "none"
                
        config.set(sample_name, "Outcome", "sample did not exist")
        continue # skip to next sample

    # submit sample to cuckoo 
    multi_part = {'file': open(loc, 'rb')}
    rqst = requests.post(cuckoo_url + submit, files=multi_part)
    resp = rqst.json()

    taskid = int(resp['task_id'])

    # save off submission info
    config.set(sample_name, 'Location', loc)
    config.set(sample_name, 'Task', taskid)

    if args.verbose:
        print sample_name + " was submitted with task ID " + str(taskid)


    # spin until done processing sample
    timeout = 600
    spent = 0
    while status is not "reported" and spent < timeout:
        wait = 60
        if args.verbose:
            print "waiting " + wait + " seconds for sample to process"
            
        time.sleep(wait)
        spent = spent + wait
        
        # check status of sample
        rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
        status = rqst.json()['task']['status']
        config.set(sample_name, 'Status', status)
        if args.verbose:
                print "at time " + spent + " status of " + sample_name + " is " + status
    
    # we're done waiting, let's try to check the report        
    if (status is not "reported"):
        config.set(sample_name, "Outcome", "cuckoo did not generate a report")    
        continue # skip to next sample

    else:
        # get report from cuckoo
        
        rqst = requests.get(cuckoo_url + report + str(taskid))
        report = rqst.json()
        category = config.get(sample_name, 'Behavior')
        ind = config.get(sample_name, 'Indicator')
    
        # check for  indicators

        if args.verbose:
            print "checking for "+ ind + " under " + category

        result =  "report FAILED"                
        # find network indicators
        if "network" in category:
            try:
                # i.e. if indicator is "http", we have a non-empty list in report[network][http]
                if report['network'][ind]:
                        result =  "report PASSED"
            except KeyError:
                print "ERR invalid config of " + category 
            
        else:
            
        # find host indicators
            try:
                # i.e. report[behavior][summary][mutexes] contains "evilmutex"
                for item in report['behavior']['summary'][category]:
                    if ind in item:
                        result =  "report PASSED"
            except KeyError:
                print "ERR invalid config of " + category 
        
        if args.verbose:
            print sample_name + " had an outcome of " + outcome
            
        config.set(sample_name, "Outcome", result)

# done processing,all samples, write output file
outfile = config_file + ".result"

if args.verbose:
    print "writing output file "+ outfile

with open(outfile, 'wb') as out:
    config.write(out)

