#!/usr/bin/env bash
set -euo pipefail
TF_DIR="$(dirname "$0")/../terraform/aws"

terraform -chdir="$TF_DIR" destroy -auto-approve -var "my_ip=$(curl -4 -s ifconfig.me)/32"

echo "==> Verifying nothing is left running:"
aws ec2 describe-instances --query 'Reservations[].Instances[].{id:InstanceId,state:State.Name}' --output table
aws ec2 describe-volumes  --query 'Volumes[].VolumeId' --output text
aws ec2 describe-addresses --query 'Addresses[].PublicIp' --output text
echo "==> All clear."