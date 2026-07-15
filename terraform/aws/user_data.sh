#!/bin/bash
# IMDSv2 token
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 300")

PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

# k3s inherits the host resolv.conf; Ubuntu's systemd-resolved stub
# (127.0.0.53) is unreachable from pod network namespaces -> SERVFAIL.
# Pinning the kubelet to the VPC resolver instead.
mkdir -p /etc/rancher/k3s
echo "nameserver 169.254.169.253" > /etc/rancher/k3s/resolv.conf

curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--tls-san ${PUBLIC_IP} --resolv-conf /etc/rancher/k3s/resolv.conf" sh -