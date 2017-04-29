#
# global variables seen within multiple modules
# Usage:
#   import globalconfig
#   globalconfig.debugflag = True

# defaults for script command-line options
debugflag = False
verboseflag = False
batchmode = False
noop = False

# UI defaults
prompt = "> "		# TODO: investigate using sys.ps2

# store variables that should only be populated once
fqdn = ""
hostname = ""		# short hostname, first part of FQDN
effectiveuser = ""	# i.e. root
humanuser = ""		# i.e. the user who becme root

# shared memory across threads

heartbeat = 0		# loop for a timer.
heartmax = 40		# 40 ticks per synchronization cycle
heartrate = 0.05  	# 20 ticks per second

polling_interval = 0.1	# talk to Jarvis 10 times a second
