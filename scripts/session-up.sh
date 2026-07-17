#!/usr/bin/env bash
set -euo pipefail

TF_DIR="$(dirname "$0")/../terraform/aws"
KEY=~/.ssh/sre-lab
KUBECONFIG_OUT=~/.kube/sre-lab.yaml

MY_IP="$(curl -4 -s ifconfig.me)/32"
echo "==> Applying (source IP: $MY_IP)"
terraform -chdir="$TF_DIR" apply -auto-approve -var "my_ip=$MY_IP" \
    -var "ssh_public_key=$(cat ~/.ssh/sre-lab.pub)"

IP="$(terraform -chdir="$TF_DIR" output -raw node_public_ip)"
echo "==> Instance up at $IP — waiting for SSH..."

until ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
      -i "$KEY" ubuntu@"$IP" true 2>/dev/null; do
  sleep 5
done

echo "==> Waiting for cloud-init (k3s install)..."
ssh -i "$KEY" ubuntu@"$IP" "cloud-init status --wait" >/dev/null

echo "==> Pulling kubeconfig"
ssh -i "$KEY" ubuntu@"$IP" "sudo cat /etc/rancher/k3s/k3s.yaml" \
  | sed "s/127.0.0.1/$IP/" > "$KUBECONFIG_OUT"
chmod 600 "$KUBECONFIG_OUT"

echo "==> Cluster ready:"
KUBECONFIG="$KUBECONFIG_OUT" kubectl get nodes
echo ""
echo "    export KUBECONFIG=$KUBECONFIG_OUT"