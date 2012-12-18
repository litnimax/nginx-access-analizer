iptables -F 

iptables -N bad_tcp_packets
iptables -A  bad_tcp_packets -p tcp --tcp-flags SYN,ACK SYN,ACK -m state --state NEW -j REJECT --reject-with tcp-reset
iptables -A bad_tcp_packets -m limit --limit 6/min -j LOG --log-prefix 'NEW-NOT-SYN: '
iptables -A bad_tcp_packets -p tcp \! --syn -m state --state NEW -j DROP

iptables -N icmp-limit
iptables -A icmp-limit -p icmp --icmp-type 0 -j ACCEPT 
iptables -A icmp-limit -p icmp --icmp-type 3 -j ACCEPT
iptables -A icmp-limit -p icmp --icmp-type 8 -m limit --limit 10/second -j ACCEPT 
iptables -A icmp-limit -p icmp --icmp-type 11 -j ACCEPT 
iptables -A icmp-limit -j DROP

iptables -N check_syn
iptables -A check_syn -p tcp -m hashlimit --hashlimit 15/min --hashlimit-burst 30 --hashlimit-mode srcip --hashlimit-name DDOS --hashlimit-htable-size 32768 --hashlimit-htable-max 32768 --hashlimit-htable-gcinterval 1000 --hashlimit-htable-expire 100000 -j RETURN
# All above goes to backlist
iptables -A check_syn -j SET --add-set syndos src


# Check for good new packets
iptables -A INPUT -p tcp -i eth0 -s 0/0 -m state --state NEW -j bad_tcp_packets

# Accept established connections
iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT

# Drop banned
iptables -A INPUT -p tcp -m set --match-set syndos src -j DROP

# Check syn limits
iptables -A INPUT -p tcp  -m state --state NEW -j check_syn

# Accept new WEB connections
iptables -A INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT

# Accept SSH
iptables -A INPUT -p tcp -m multiport --dports 22 -j ACCEPT

# Filter ICMP
	iptables -A INPUT -p icmp -j icmp-limit

# Accept local traffic
iptables -A INPUT -i lo -j ACCEPT -m comment --comment 'Loopback'

# Finish'em
iptables -A INPUT -p tcp -m limit --limit 6/minute -j LOG --log-level debug --log-prefix 'TCP-LOST:'
iptables -A INPUT -p tcp -j DROP
iptables -A INPUT -m limit --limit 6/minute -j LOG --log-level debug --log-prefix 'NONTCP-DROP:'
iptables -A INPUT -j DROP
