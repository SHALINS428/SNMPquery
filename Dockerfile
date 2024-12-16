FROM alpine:latest
RUN apk add --no-cache net-snmp net-snmp-tools
COPY snmpd.conf /etc/snmp/snmpd.conf
CMD ["/usr/sbin/snmpd", "-f", "-Lo"]
