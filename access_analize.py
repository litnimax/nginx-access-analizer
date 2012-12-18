#!/usr/bin/python

import commands, re
import os, sys, time

LOCK_DIR = '/var/lock/'

LOG_FILES = ['/var/log/nginx/asterisk-support.ru-access.log']

EXCEPT_URL_REGEX = '/feeds/'

HITCOUNT_PER_URL_RATIO = 10 # 
MAX_URLS_BOT_CAN_USE = 3 # Our bots are stupid and fetch only 2  urls

DRY_RUN = len(sys.argv) > 1 and sys.argv[1] == '-dry'

ip_re = re.compile(r'[0-9]+(?:\.[0-9]+){3}')

ban_count = 0

for log_file in LOG_FILES:

    file_name = os.path.basename(log_file)
    lock_file = os.path.join(LOCK_DIR, '%s.state' % file_name)

    # Try to get last position
    position = 0
    if os.path.isfile(lock_file):
	try:
	    position = int(open(lock_file, 'r').read())
	except ValueError:
	    position = 0

    # Now open log file and forward
    log_data = open(log_file, 'r')
    try:
    	log_data.seek(position)
    except IOError: 
	# File was rotated and stored position is greater then file size.
	position = 0

    # Now create tmp file for shell tools
    tmp_file_handle = open('/tmp/nginx_access_%s.tmp' % time.time(), 'w')
    tmp_file_handle.write(log_data.read())

    # Clock to seek buffers as shell tools will open and read it.
    tmp_file_handle.close()

    # list of ip addresses noticed in log 
    ip_list = commands.getoutput("cat %s| awk '{print $1}' | sort | uniq | sort -n" % tmp_file_handle.name).split()

    # Now let check ip addresses
    for ip in ip_list:
	# Let see if we really grep by x.x.x.x
	if not ip_re.search(ip):
	    continue
	# Not really effective but quick and fun :-) Python would take more time for me.	
	hits = len(commands.getoutput("cat %s | grep %s | awk '{print $7}'" % (tmp_file_handle.name, ip)).split())
	urls = commands.getoutput("cat %s | grep %s | grep -v %s | awk '{print $7}' | sort | uniq | sort -n" % (tmp_file_handle.name, ip, EXCEPT_URL_REGEX)).split()
	# We check later that urls list can be empty due to grep -v
	# Here are our brains :-))
	if len(urls) and (hits / len(urls)) > HITCOUNT_PER_URL_RATIO and len(urls) <= MAX_URLS_BOT_CAN_USE:
		print 'Banning fuckin bot: %s, hits: %s, total urls: %s' % (ip, hits, len(urls))
		if not DRY_RUN:
		    status, output = commands.getstatusoutput('ipset add bandos %s' % ip)
		    if status not in [0, 256]: #256 - already there
			print 'ipset returned %s: %s' % (status, output)
		ban_count += 1
		for url in urls:
		    print '\t- ', url
    # remove tmp file
    os.unlink(tmp_file_handle.name)
    if not DRY_RUN: 
	open(lock_file, 'w').write('%s' % log_data.tell())
    log_data.close()

print '-------------------'
print "Banned %s bots. Fuck'em off! ;-)" % ban_count
