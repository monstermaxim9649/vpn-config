#!/bin/bash
docker exec xray-reality sh -c "cat /var/log/xray/access.log | tail -n 50 | grep -o 'email: [^ ]*' | cut -d' ' -f2 | sort -u"
