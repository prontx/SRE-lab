#!/bin/bash
# IMDSv2: get a session token first
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 300")

PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--tls-san ${PUBLIC_IP}" sh -