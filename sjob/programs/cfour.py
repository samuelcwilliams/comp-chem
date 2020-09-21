import math
import sys
import os
import re

def check_input(args,nodeInfo):

  def red(phrase): return("\033[31;1m"+phrase+"\033[0m") 
  
  errors = []
  def error(messages):
    for message in messages:
      print(message)
    print("Use --no-parse to ignore error(s)")
    sys.exit(1)

  # Parse Input File and perform checks
  def convert_mem_units(memory, iUnits):
    # Conversion factors from denoted units to MB
    memConv = {"INTEGERWORDS": 7.62939*math.pow(10,-6), "KB": 1/1024.0, "MB": 1.0, "GB": 1024, "TB": math.pow(1024.0,2)}
    return memory * memConv[iUnits]
  def clean_job_line(line):
    if "*CFOUR(" in line: line = line.split("*CFOUR(")[1]
    if ")" in line: line = line.split(")")[0]
    line = line.lstrip(" ").rstrip("\n").rstrip(" ")
    return line.upper()
  def parse_job_line(line, keywords):
    items = line.split(",")
    for item in items: keywords.update({item.split("=")[0]: item.split("=")[1]})
  def find_job_item(keywords, item_names, throw_error):
    for name in item_names:
      if name in keywords: return keywords[name]
    if throw_error:
      errors.append(" or ".join(item_names)+" not found in keyword list")
      error(errors)
    else:
      return False

  keywords = {}
  inputData = open(args['input'],"r").readlines()
  for i in range(0, len(inputData)):
    if "*CFOUR" in inputData[i] or "*ACES2" in inputData[i] or "*CRAPS" in inputData[i]:
      for j in range(i, len(inputData)):
        if len(inputData[j].split()) < 1: break
        else: parse_job_line(clean_job_line(inputData[j]), keywords)

  if args['parseInput']:
    # find job type
    jobType = ""
    vibration = find_job_item(keywords, ["VIB", "VIBRATION"], False)
    if vibration:
      jobType = "Frequencies"
    else:
      for line in inputData[1:]:
        if "*CFOUR" in line or "*ACES2" in line or "*CRAPS" in line:
          jobType = "Energy"
          break
        elif "*" in line:
          jobType = "Optimization"
          break
    if jobType == "":
      errors.append(red("ERROR")+": job type not found")
      error(errors)

    # check for CC pitfalls (aobasis, cc_prog, fcgradnew, frozen_core)
    abcdtype = find_job_item(keywords, ["ABCDTYPE"], False)
    calclevel = find_job_item(keywords, ["CALC", "CALCLEVEL"], False)
    reference = find_job_item(keywords, ["REFERENCE"], False)
    if not reference: reference = "RHF"
    cc_prog = find_job_item(keywords, ["CC_PROG", "CC_PROGRAM"], False)
    if not cc_prog: cc_prog = "VCC"
    frozen_core = find_job_item(keywords, ["FROZEN_CORE"], False)
    fcgradnew = find_job_item(keywords, ["FCGRADNEW"], False)
    basis = find_job_item(keywords, ["BASIS"], False)
    if "CC" in calclevel:
      if abcdtype != "AOBASIS":
        errors.append(red("ERROR")+": ABCDTYPE keyword not set for coupled cluster job")
      if reference == "RHF" or reference == "UHF":
        if cc_prog != "ECC":
          errors.append(red("ERROR")+": CC_PROGRAM keyword not set to ECC for RHF or UHF reference")
      elif reference == "ROHF" and jobType != "Energy":
        if cc_prog != "VCC":
          errors.append(red("ERROR")+": CC_PROGRAM keyword not set to VCC for ROHF REFERENCE and OPT/FREQ job type")
      if frozen_core == "ON":
        if fcgradnew != "NEW":
          errors.append(red("ERROR")+": FCGRADNEW keyword not set to NEW for frozen core coupled cluster job")
    match = re.match("[pP]V[DTQ56]Z", basis)
    if match:
      if frozen_core != "ON":
        errors.append(red("ERROR")+": Frozen core basis set selected without setting FROZEN_CORE keyword to ON")

    # Checking for Appropriate Job Memory
    jobMemory = find_job_item(keywords, ["MEM","MEMORY"], False)
    if jobMemory:
      jobMemory = int(jobMemory)
      jobMemUnit = find_job_item(keywords, ["MEM_UNIT"], False)
      if jobMemUnit: # Convert Memory to MB
        jobMemory = convert_mem_units(jobMemory, jobMemUnit.upper())
      else:
        jobMemory = convert_mem_units(jobMemory, "INTEGERWORDS")
    nodeMemLimit = nodeInfo[args['queue']]['nodeMem'] * 0.95 / args['nslot']
    if jobMemory > nodeMemLimit: # Check if memory is more than 90% of Node
      errors.append(red("ERROR")+": Please reduce the memory of your job from "+str(jobMemory)+" MB to "+str(int(nodeMemLimit))+" MB or less for "+str(args['nslot'])+" processors")
    # If the user is performing a transition state search REQUIRE a FCMINT file.
    geomTS = find_job_item(keywords, ["GEO_METHOD"], False)
    if geomTS:
        if geomTS == "TS" or geomTS == "2":
            if not os.path.exists("FCMINT"):
                errors.append("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                errors.append("  You requested a transition state (TS) search without providing an FCMINT file.")
                errors.append("  Without this file you are wasting computer time!")
                errors.append("  Run a frequency calculation first and use the resulting FCMINT file here.")
                errors.append("    Your job will not be submitted.")
                errors.append("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    if errors: error(errors)

def footer(args,cluster):
  job_id = "PBS_JOBID"
  workdir = "PBS_O_WORKDIR"
  cmd = "strip=(${PBS_JOBID//./ })\n"
  job_id = "${strip[0]}.${strip[1]}"

  # Explicity list the files we want to save because there will be other crap in there
  toSave = ['FCMINT',
            'FCMFINAL',
            'ZMATnew',
            'JMOLplot',
            'JOBARC',
            'JAINDX',
            'FJOBARC',
            'DIPDER',
            'HESSIAN',
            'MOLDEN',
            'MOLDEN_NAT',
            'NEWMOS',
            'AVOGADROplot.log']
  cmd1 = "tar --transform \"s,^,Job_Data_%s/,\" -vcf ${%s}/Job_Data_%s.tar %s\n" % (job_id, workdir, job_id, ' '.join(toSave))

  # The shell will error is zmat* does not match an existing file, so we must test for their presence.
  toSave = ['zmat*']
  cmd2 = "if [ -e zmat001 ]; then tar --transform \"s,^,Job_Data_%s/,\" -vrf ${%s}/Job_Data_%s.tar %s; fi\n" % (job_id, workdir, job_id, ' '.join(toSave))
  cmd3 = "gzip ${%s}/Job_Data_%s.tar\n" % (workdir, job_id)

  # delete scratch directory
  cmd4 = "cd $PBS_O_WORKDIR\n"
  cmd5 = "rm -r $SCRATCH\n"

  return cmd + cmd1 + cmd2 + cmd3 + cmd4 + cmd5

