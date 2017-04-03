#!/bin/bash
iptables -P INPUT ACCEPT
iptables -F
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# Allow icmp ping
iptables -A INPUT -p icmp --icmp-type 8 -s 0/0  -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p icmp --icmp-type 0 -d 0/0 -m state --state ESTABLISHED,RELATED -j ACCEPT
# Services
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
#iptables -A INPUT -p tcp --dport 8080 -j ACCEPT -m comment --comment "Tomcat6/Thredds"
#iptables -A INPUT -p tcp --dport 9080 -j ACCEPT -m comment --comment "Apache/SVN"
#iptables -A INPUT -p tcp --dport 8443 -j ACCEPT -m comment --comment "Tomcat6/Thredds SSL"
iptables -A INPUT -p tcp --dport 443 -j ACCEPT -m comment --comment "Nginx SSL proxy to services"
iptables -A INPUT -p tcp --dport 80 -j ACCEPT -m comment --comment "Nginx"
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT -m comment --comment "django development"
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
iptables -L -v
