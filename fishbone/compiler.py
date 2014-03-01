# Copyright (c) 2011, Jon Clement
# All rights reserved.

# May 4, 2011 - one of my first python apps

# This 'compiler' produces a yaml definitions file.
# It contains the acceptible way that functions can be call
# ie/ By the finite state machine (continuation, fan out,)
# OR local/offline execution possible

import os
import sys
import re

my_functions=[]
# Hard code path
path="c:\\scripts\\panamantis\\functions"
dirList=os.listdir(path)
for file in dirList:
	file.rstrip('\n')
	temp=""
	m = re.search('(.*)\.(.*)', file)
	if m:
		temp=str(m.group(2))
	if (temp=="py"):
		my_functions.append(m.group(1))

# Create panamantis.yaml
temp=path+"\\function_lookup.py"
print "Creating: "+temp
f=open(temp,"w")
f.write('function_lookup = {'+"\n")
first=1

#parameters=[]
for function in my_functions:
#deb	print function
	file = open(path+"\\"+function+".py")
	for line in file:
		line.rstrip('\n')
		# Grab latest def (??or class??) name
		n = re.search('def (.*)\(.*', line)
		if n:
			def_name=str(n.group(1))
		# Grab data line
		m = re.search('\#.*panamantis(.*)', line)
		if m:
			temp=str(m.group(1))
			parameters=temp.split(",",3)
			if (first):
				first=0
			else:
				f.write(",\n")
			myentry="    \'"+parameters[1]+"\': \'"+parameters[2]+"\'"
			print myentry
			f.write(myentry)
f.write("\n"+'}')
f.close()
