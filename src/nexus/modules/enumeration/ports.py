"""Offline well-known port / service lookup.

A curated table of the TCP/UDP ports an analyst meets most often during
enumeration. Lookups work by number or by service-name substring, with no
network access.
"""
from __future__ import annotations

from typing import Dict, List

# port -> (service, protocol, description)
PORTS: Dict[int, tuple[str, str, str]] = {
    20: ("ftp-data", "tcp", "FTP data transfer"),
    21: ("ftp", "tcp", "FTP control"),
    22: ("ssh", "tcp", "Secure Shell / SFTP / SCP"),
    23: ("telnet", "tcp", "Telnet (cleartext remote shell)"),
    25: ("smtp", "tcp", "Mail transfer"),
    37: ("time", "tcp", "Time protocol"),
    43: ("whois", "tcp", "WHOIS directory service"),
    53: ("dns", "tcp/udp", "Domain Name System"),
    67: ("dhcp", "udp", "DHCP server"),
    68: ("dhcp", "udp", "DHCP client"),
    69: ("tftp", "udp", "Trivial FTP"),
    80: ("http", "tcp", "Hypertext Transfer Protocol"),
    88: ("kerberos", "tcp/udp", "Kerberos authentication"),
    110: ("pop3", "tcp", "Post Office Protocol v3"),
    111: ("rpcbind", "tcp/udp", "ONC RPC / portmapper"),
    119: ("nntp", "tcp", "Network News Transfer"),
    123: ("ntp", "udp", "Network Time Protocol"),
    135: ("msrpc", "tcp", "Microsoft RPC endpoint mapper"),
    137: ("netbios-ns", "udp", "NetBIOS name service"),
    138: ("netbios-dgm", "udp", "NetBIOS datagram"),
    139: ("netbios-ssn", "tcp", "NetBIOS session (SMB over NetBIOS)"),
    143: ("imap", "tcp", "Internet Message Access Protocol"),
    161: ("snmp", "udp", "Simple Network Management"),
    162: ("snmptrap", "udp", "SNMP trap"),
    179: ("bgp", "tcp", "Border Gateway Protocol"),
    389: ("ldap", "tcp/udp", "Lightweight Directory Access"),
    443: ("https", "tcp", "HTTP over TLS"),
    445: ("microsoft-ds", "tcp", "SMB / CIFS direct"),
    464: ("kpasswd", "tcp/udp", "Kerberos password change"),
    465: ("smtps", "tcp", "SMTP over TLS"),
    500: ("isakmp", "udp", "IPsec / IKE"),
    514: ("syslog", "udp", "Syslog"),
    515: ("printer", "tcp", "Line Printer Daemon"),
    587: ("submission", "tcp", "SMTP mail submission"),
    623: ("ipmi", "udp", "IPMI / BMC remote management"),
    636: ("ldaps", "tcp", "LDAP over TLS"),
    873: ("rsync", "tcp", "rsync file sync"),
    989: ("ftps-data", "tcp", "FTP data over TLS"),
    990: ("ftps", "tcp", "FTP control over TLS"),
    993: ("imaps", "tcp", "IMAP over TLS"),
    995: ("pop3s", "tcp", "POP3 over TLS"),
    1080: ("socks", "tcp", "SOCKS proxy"),
    1194: ("openvpn", "udp", "OpenVPN"),
    1337: ("waste", "tcp", "Often used for ad-hoc / CTF services"),
    1433: ("ms-sql-s", "tcp", "Microsoft SQL Server"),
    1521: ("oracle", "tcp", "Oracle database listener"),
    1723: ("pptp", "tcp", "PPTP VPN"),
    2049: ("nfs", "tcp/udp", "Network File System"),
    2082: ("cpanel", "tcp", "cPanel"),
    2375: ("docker", "tcp", "Docker API (unencrypted)"),
    2376: ("docker-s", "tcp", "Docker API (TLS)"),
    27017: ("mongodb", "tcp", "MongoDB"),
    3000: ("dev-http", "tcp", "Common dev server (Node, Grafana, Rails)"),
    3306: ("mysql", "tcp", "MySQL / MariaDB"),
    3389: ("rdp", "tcp", "Remote Desktop Protocol"),
    4444: ("metasploit", "tcp", "Common Metasploit / reverse-shell handler"),
    5000: ("dev-http", "tcp", "Common dev server (Flask, UPnP)"),
    5432: ("postgresql", "tcp", "PostgreSQL"),
    5601: ("kibana", "tcp", "Kibana"),
    5672: ("amqp", "tcp", "RabbitMQ / AMQP"),
    5900: ("vnc", "tcp", "VNC remote desktop"),
    5985: ("winrm-http", "tcp", "Windows Remote Management (HTTP)"),
    5986: ("winrm-https", "tcp", "Windows Remote Management (HTTPS)"),
    6379: ("redis", "tcp", "Redis"),
    6667: ("irc", "tcp", "Internet Relay Chat"),
    8000: ("http-alt", "tcp", "Alternate HTTP / dev server"),
    8080: ("http-proxy", "tcp", "HTTP proxy / alternate web"),
    8443: ("https-alt", "tcp", "Alternate HTTPS"),
    8888: ("http-alt", "tcp", "Alternate HTTP / Jupyter"),
    9000: ("http-alt", "tcp", "SonarQube / PHP-FPM / dev"),
    9200: ("elasticsearch", "tcp", "Elasticsearch"),
    9418: ("git", "tcp", "Git protocol"),
    11211: ("memcached", "tcp/udp", "Memcached"),
    1: ("tcpmux", "tcp", "TCP port service multiplexer"),
}


def lookup_port(number: int) -> List[Dict]:
    """Return the service entry for a port number, if known."""
    entry = PORTS.get(number)
    if not entry:
        return []
    service, proto, desc = entry
    return [{"port": number, "service": service, "protocol": proto, "description": desc}]


def search_service(term: str) -> List[Dict]:
    """Find ports whose service name or description matches a search term."""
    term = term.lower().strip()
    hits: List[Dict] = []
    for number, (service, proto, desc) in sorted(PORTS.items()):
        if term in service.lower() or term in desc.lower():
            hits.append({"port": number, "service": service, "protocol": proto, "description": desc})
    return hits


def resolve(query: str) -> Dict:
    """Resolve a query that is either a port number or a service name."""
    q = query.strip()
    if q.isdigit():
        results = lookup_port(int(q))
        kind = "port"
    else:
        results = search_service(q)
        kind = "service"
    return {"query": q, "kind": kind, "matches": results, "count": len(results)}
