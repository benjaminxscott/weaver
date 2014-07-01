#!/usr/bin/env python
import requests
import sys
import os
import json
import ConfigParser
import time
import argparse

# REF cuckoo API endpoints
statcheck = "/cuckoo/status"
taskcheck = "/tasks/view/"
tasklist = "/tasks/list"
submit = "/tasks/create/file"
report = "/tasks/report/"

# get args
parser = argparse.ArgumentParser ( formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description = "Automatic submission suite for cuckoobox, meant for testing / verification of sandbox images. \n"
            + "Takes a configuration file listing the sample name and success criteria")
parser.add_argument("--config", help="configuration file", default="sample.cfg") 
parser.add_argument("--cuckoo", help="URL and port for cuckoo server API", default="http://localhost:8090") 
parser.add_argument("-v","--verbose", help="have verbose output", action='store_true') 

args = parser.parse_args()

# check that cuckoo is up
cuckoo_url = args.cuckoo

try:
    rqst = requests.get(cuckoo_url + statcheck)

except:
    print "ERR: cuckoo server at " + cuckoo_url + " appears to be unresponsive - exiting"
    sys.exit(1)


# load config
config_file = args.config

config = ConfigParser.RawConfigParser()

if not config.read(config_file) :
    print "ERR: Configuration file did not exist: " + config_file
    exit(1)


# Submit each sample and wait for results

for sample_name in config.sections():

    # try to find sample under current dir
    found = False
    for root,d,filename in os.walk("."):
        if sample_name in filename:
            loc = os.path.join(root, sample_name)
            found = True
            break
        if not found:
            print "ERR sample " + sample_name + "did not exist"
            config.set(sample_name, "Outcome", "sample did not exist")
            continue # skip to next sample

    # submit sample to cuckoo 
    multi_part = {'file': open(loc, 'rb')}
    rqst = requests.post(cuckoo_url + submit, files=multi_part)

    try:
        resp = rqst.json()
        taskid = int(resp['task_id'])
        status = "submitted"
        if args.verbose:
            print sample_name + " was submitted with task ID " + str(taskid)
    except:
        config.set(sample_name, "Outcome", "error in cuckoo response")
        continue # skip to next sample

    # save off submission info
    config.set(sample_name, 'Location', loc)
    config.set(sample_name, 'Task', taskid)

    # spin until done processing sample
    timeout = 600
    spent = 0
    while status != "reported" and spent < timeout :
        wait = 60
        if args.verbose:
            print "waiting " + str(wait) + " seconds for sample to process"
            
        time.sleep(wait)
        spent = spent + wait
        
        # check status of sample
        rqst = requests.get(cuckoo_url + taskcheck + str(taskid))
        status = rqst.json()['task']['status']
        config.set(sample_name, 'Status', status)
        if args.verbose:
                print "at time " + str(spent) + " status of " + sample_name + " is " + status
    
    # we're done waiting, let's try to check the report        
    if (status != "reported"):
        config.set(sample_name, "Outcome", "cuckoo did not generate a report")    
        continue # skip to next sample

    else:
        # get report from cuckoo
        rqst = requests.get(cuckoo_url + report + str(taskid))
        report = rqst.json()
    
        # collect indicators from config
        detections = zip(config.get(sample_name, 'Section').split(','), config.get(sample_name, 'Indicator').split(','))

        found = False
        for i, (section, ind) in enumerate(detections):
            if args.verbose:
                print "checking " + sample_name + " for "+ ind + " under " +section

            # - find network indicators
            if "network" in section:
                try:
                    # i.e. if indicator is "http", we have a non-empty list in report[network][http]
                    if report['network'][ind]:
                        found=  True
                    else:
                        found = False
                except KeyError:
                    print "ERR invalid config value " +section 
                
            else:
            # - examine host indicators
                try:
                    # i.e. report[behavior][summary][mutexes] contains "evilmutex"
                    for item in report['behavior']['summary'][section]:
                        if ind in item:
                            found=  True
                            break
                        else:
                            found = False
                except KeyError:
                    print "ERR invalid config value " +section 
            
            if args.verbose:
                print "Were indicators for " + sample_name + " in report? " + str(found)
            
            # short-circuit if one indicator is not found 
            # allows AND behavior for multiple indicators
            if found == False:
                break

        # end for
                
        # log result
        if found: 
            config.set(sample_name, "Outcome", "SUCCESS")
        else: 
            config.set(sample_name, "Outcome", "report did not contain all specified indicators")


# done processing,all samples, write output file
outfile = config_file + ".result"

if args.verbose:
    print "writing output file "+ outfile

with open(outfile, 'wb') as out:
    config.write(out)

