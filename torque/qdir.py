#!/opt/miniconda3/envs/python2.7/bin/python

# becase this is called from a bash script, the first thing printed is what gets sent to 'cd'

import commands
import xml.etree.ElementTree as ET
import sys
import os

def qstat(path,jobId):
    if os.path.exists(path): return commands.getoutput(path+" -f -x "+jobId) 
    else: 
        print("qstat command not found...exiting.")
        sys.exit()

def find_job_data(qstatXml):
    jobDir = qstatXml.find("Job").find('Output_Path').text.split(":")[1]
    jobDir = jobDir[:jobDir.rfind("/")]
    return jobDir

jobId = sys.argv[1]

qstatReturn = qstat(commands.getoutput("which qstat"),jobId)
if "Unknown Job Id" in qstatReturn:
    print("Job_no_longer_listed_in_qstat")
    sys.exit()
else:
    qstatXml = ET.fromstring(qstatReturn)

path = find_job_data(qstatXml)

print(path)

