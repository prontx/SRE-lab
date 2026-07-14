# Cloud-Native lab

Leveraging my 5 years of OpenStack/RHOSP
production support engineering experience to cloud-native SRE practice. Everything here is
built from scratch, provisioned as code, and destroyed after each session.

![Node Exporter dashboard on the lab cluster](docs/grafana-node-exporter.png)

## Contents

### `terraform/aws/` — Infrastructure as Code on AWS ✅
- VPC, subnet, routing (IGW, route tables) assembled explicitly — the AWS
  equivalent of what Neutron's `router-gateway-set` does implicitly
- EC2 provisioning with SSH keypair management and AMI lookup via data sources
  (no hardcoded, region-rotting AMI IDs)
- Security groups parameterized by source IP (`-var my_ip=...`)
- k3s single-node Kubernetes bootstrapped at boot via cloud-init `user_data`,
  with the public IP injected into the API cert SANs via IMDSv2 at boot
- State hygiene: tfstate excluded from VCS, provider versions pinned via lock file

### `scripts/` — session automation ✅
- `session-up.sh`: apply -> wait for SSH -> wait for cloud-init -> pull kubeconfig -> ready
- `session-down.sh`: destroy → verify no instances/volumes/EIPs left behind

### `k8s/` — Kubernetes ops
- Remote kubectl access (TLS SAN problem — see below) ✅
- Helm-deployed observability: kube-prometheus-stack (Prometheus, Grafana,
  node-exporter, kube-state-metrics) with values override ✅
- Loki for logs — planned
- GitOps with Flux/ArgoCD — planned
- CI/CD via GitHub Actions — planned

## Incidents & lessons so far

Real problems hit and diagnosed along the way:

- **"TLS handshake timeout" on localhost kubectl** -> not a TLS problem.
  Diagnosed via `free -m` / `dmesg` / `top` as memory starvation: k3s control
  plane on a 1GB t3.micro left 29MB available. Symptoms lie about their layer.
  Fixed by right-sizing to t3.small.
- **Same signature, round two**: deploying kube-prometheus-stack starved the
  2GB node the same way — recognized it on sight this time. Empirical sizing
  rule derived: bare k3s needs 2GB, k3s + a real workload needs 4GB+.
- **Free-tier constraint discovery**: t3.medium rejected as not free-tier
  eligible. Read the error, ran `describe-instance-types
  --filters free-tier-eligible=true`, found m7i-flex.large (8GB) in the
  allowed list — better than the original plan.
- **Instance stop/start ≠ recreate**: resizing stops/starts the instance;
  cloud-init doesn't rerun but the public IP changes, leaving the boot-time
  TLS cert stale. Anything configured at boot goes stale when runtime identity
  changes. Fix: destroy and recreate.
- **Drift detection in practice**: manually tagged a VPC in the console,
  watched `terraform plan` propose reverting it.
- **State is the boundary of Terraform's world**: tagged the wrong (default)
  VPC, Terraform didn't blink. Resources outside state are invisible.

## Background

The mental model transfer from OpenStack is the point of this repo:

| OpenStack        | AWS / cloud-native          |
|------------------|-----------------------------|
| Neutron network  | VPC                         |
| router-gateway   | Internet Gateway + routes   |
| Floating IP      | Elastic IP / auto-assign    |
| Heat             | Terraform / CloudFormation  |
| Heat parameters  | Terraform variables         |
| Glance image     | AMI (per-region!)           |
| Keystone 403     | IAM deny-by-default         |
| config-drive / metadata API | IMDSv2           |

## TODO
- [ ] Least-privilege IAM policy for the terraform user (lab currently uses AdministratorAccess)
- [ ] Remote state backend (S3 + DynamoDB locking)
- [ ] Loki + log pipeline
- [ ] GitOps: Flux syncing k8s/ from this repo
- [ ] GitHub Actions: terraform fmt/validate on PR
- [ ] Multi-node k3s
- [ ] Terraform mirror against OpenStack provider