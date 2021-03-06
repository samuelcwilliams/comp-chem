import math
import sys
import re

def check_input(args,nodeInfo):

  def error(message):
    print(message)
    sys.exit(1)

  def convert_mem_units(memory, iUnits):
    memConv = {'': math.pow(131072,-1), 'real': math.pow(131072,-1), 'double': math.pow(131072,-1), 'integer': math.pow(131072,-1), 'byte': math.pow(1024,-2), 'kb': math.pow(1024,-1), 'mb': 1.0, 'mw': 8.0}
    return memory * memConv[iUnits]

  # main
  if args['parseInput']:
    inputData = open(args['input'],'r').read()
    memMatch = re.search(r'memory\s*(\d+)\s*([a-zA-Z]*)',inputData,re.IGNORECASE)
    nodeMemLimit = nodeInfo[args['queue']]['nodeMem'] * 0.95 / args['nslot']
    if memMatch:
      jobMemory = int(memMatch.group(1))
      jobMemUnit = memMatch.group(2).lower()
      jobMemory = convert_mem_units(jobMemory, jobMemUnit)
      if jobMemory > nodeMemLimit:
        error('Please reduce the memory of your job from '+str(int(jobMemory))+' MB to '+str(int(nodeMemLimit))+' MB or less for '+str(args['nslot'])+' processors')
    else:
      print('Memory card not found.  Max memory allowed is '+str(int(nodeMemLimit))+' m. Default is unknown....')

def footer(args,cluster):
    file_prefix = args['input'].split(".")[0]
    cmd = "if [ -e %s.movecs ]; then cp -f %s.movecs $PBS_O_WORKDIR/%s.movecs; fi \n" % (file_prefix,file_prefix,file_prefix)
    cmd2 = "rm -r $TMPDIR\n"
    return cmd + cmd2

