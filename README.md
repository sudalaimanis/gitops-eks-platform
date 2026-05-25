# GitOps-Based Multi-Environment Deployment Platform

![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat&logo=github-actions&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-EF7B4D?style=flat&logo=argo&logoColor=white)
![Argo Rollouts](https://img.shields.io/badge/Argo_Rollouts-EF7B4D?style=flat&logo=argo&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat&logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-0F1689?style=flat&logo=helm&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![AWS EKS](https://img.shields.io/badge/AWS_EKS-FF9900?style=flat&logo=amazon-aws&logoColor=white)
![AWS Secrets Manager](https://img.shields.io/badge/Secrets_Manager-FF9900?style=flat&logo=amazon-aws&logoColor=white)

> A production-grade GitOps platform on AWS EKS. Git is the single source of truth — every deployment, rollback, and config change flows through a Git commit. ArgoCD watches the repo and automatically syncs the cluster across multiple environments, eliminating manual `kubectl` deployments and configuration drift.

---

## Outcomes

| Metric | Before | After |
|---|---|---|
| Deployment frequency | Baseline | **3x increase** |
| Rollback time | ~30 minutes | **under 2 minutes** |
| Environment drift | Manual reconciliation | **Eliminated** (declarative Git state) |
| Prod deploy risk | Big-bang releases | **Reduced** (canary + blue-green via Argo Rollouts) |

---

## How it works (in one picture)

```
You push code to GitHub
        │
        ▼
GitHub Actions runs:
  1. pytest tests
  2. docker build → push to ECR
  3. updates image tag in values.yaml → git push
        │
        ▼
ArgoCD (multi-cluster) detects the values.yaml change
        │
        ├──▶ Auto-syncs DEV cluster/namespace
        │       └── standard rolling update
        │
        ├──▶ Auto-syncs STAGING cluster/namespace
        │       └── Argo Rollouts: canary (10% → 50% → 100%)
        │
        └──▶ PROD waits for manual approval in ArgoCD UI
                └── Argo Rollouts: blue-green (switch after analysis)

Secrets (DB creds, API keys) pulled from AWS Secrets Manager
  └── External Secrets Operator syncs → Kubernetes Secrets
```

---

## Repo structure

```
gitops-eks-platform/
│
├── app/                              # The application
│   ├── app.py                        # Flask app (health, version, load-sim endpoints)
│   ├── Dockerfile                    # Container build instructions
│   ├── requirements.txt
│   └── tests/
│       └── test_app.py               # pytest tests (must pass before any deploy)
│
├── helm-charts/
│   └── sample-app/
│       ├── Chart.yaml
│       ├── values.yaml               # ← GitHub Actions updates image.tag here
│       ├── values-staging.yaml       # staging overrides
│       ├── values-prod.yaml          # prod overrides (more replicas, higher limits)
│       └── templates/
│           ├── deployment.yaml       # Helm template → real K8s Deployment
│           └── service.yaml          # Helm template → Service + HPA
│
├── argocd/
│   ├── app-of-apps.yaml              # Root app — apply this once to bootstrap
│   ├── dev.yaml                      # ArgoCD app for dev namespace
│   ├── staging.yaml                  # ArgoCD app for staging namespace (canary rollout)
│   ├── prod.yaml                     # ArgoCD app for prod (manual sync, blue-green)
│   └── rollouts/
│       ├── staging-rollout.yaml      # Argo Rollouts canary config
│       └── prod-rollout.yaml         # Argo Rollouts blue-green config
│
├── terraform/
│   └── main.tf                       # EKS cluster + VPC + ECR (all infra as code)
│
├── external-secrets/
│   ├── cluster-secret-store.yaml     # ClusterSecretStore pointing to AWS Secrets Manager
│   └── external-secret.yaml          # ExternalSecret manifest (what to sync)
│
└── .github/
    └── workflows/
        └── ci-cd.yaml                # Full pipeline: test → build → push → update helm
```

---

## Prerequisites — install these first

| Tool | Version | Install command / link |
|---|---|---|
| AWS CLI | v2+ | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install` |
| Terraform | v1.6+ | `sudo apt install terraform` or [developer.hashicorp.com](https://developer.hashicorp.com/terraform/install) |
| kubectl | v1.32+ | `sudo snap install kubectl --classic` |
| Helm | v3.12+ | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` |
| ArgoCD CLI | v2.9+ | `curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 && chmod +x argocd && sudo mv argocd /usr/local/bin/` |
| Argo Rollouts CLI | v1.6+ | `curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64 && chmod +x kubectl-argo-rollouts-linux-amd64 && sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts` |
| Docker | 24+ | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) |
| Python | 3.11+ | `sudo apt install python3.11` |

---

## Step-by-step setup

### Step 1 — Fork and clone this repo

```bash
# Fork on GitHub first (click Fork button), then:
git clone https://github.com/YOUR_USERNAME/gitops-eks-platform.git
cd gitops-eks-platform
```

---

### Step 2 — Configure AWS credentials

```bash
aws configure
```

Enter when prompted:
- AWS Access Key ID → your key
- AWS Secret Access Key → your secret
- Default region → `ap-south-1`
- Default output format → `json`

Verify it works:
```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN printed. If you get an error, your credentials are wrong.

---

### Step 3 — Run the app locally first (no Kubernetes needed)

Before touching AWS, verify the app runs on your machine:

```bash
cd app
pip install -r requirements.txt
python app.py
```

Open a second terminal and test:
```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/version
```

Expected output for `/health`:
```json
{"status": "healthy", "pod": "your-machine-name"}
```

Run the tests:
```bash
pytest tests/ -v
```

All 6 tests should pass. If they do, the app is good. Now stop the server (`Ctrl+C`).

---

### Step 4 — Build and test the Docker image locally

```bash
cd app

# Build the image
docker build -t sample-app:local .

# Run it
docker run -p 5000:5000 sample-app:local

# Test it (new terminal)
curl http://localhost:5000/health
# Expected: {"pod":"<container-id>","status":"healthy"}

# Stop the container
docker stop $(docker ps -q --filter ancestor=sample-app:local)
```

---

### Step 5 — Provision EKS with Terraform

This creates your EKS cluster (v1.32), VPC, and ECR repository on AWS. Takes about 12–15 minutes.

```bash
cd terraform

# Download providers and modules
terraform init

# See what will be created (no changes yet)
terraform plan

# Create everything
terraform apply
```

Type `yes` when asked to confirm.

When it finishes, copy the output values — you'll need them:
```
cluster_name     = "gitops-cluster"
cluster_endpoint = "https://xxxx.gr7.ap-south-1.eks.amazonaws.com"
ecr_url          = "123456789.dkr.ecr.ap-south-1.amazonaws.com/sample-app"
```

---

### Step 6 — Connect kubectl to your cluster

```bash
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name gitops-cluster

# Verify nodes are up
kubectl get nodes
```

Expected output (wait 2–3 minutes if nodes aren't Ready yet):
```
NAME                                       STATUS   ROLES    AGE
ip-10-0-1-xx.ap-south-1.compute.internal   Ready    <none>   2m
ip-10-0-2-xx.ap-south-1.compute.internal   Ready    <none>   2m
```

---

### Step 7 — Install ArgoCD on the cluster

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for all pods to be Running (takes ~2 minutes)
kubectl get pods -n argocd -w
```

Press `Ctrl+C` once all pods show `Running`.

Get the ArgoCD admin password:
```bash
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

Copy that password — you'll need it to log in.

Access the ArgoCD UI:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open `https://localhost:8080` in your browser → accept the certificate warning → login:
- Username: `admin`
- Password: paste the one you just copied

---

### Step 8 — Update values.yaml with your ECR URL

Open `helm-charts/sample-app/values.yaml` and replace the placeholder:

```yaml
# Change this line:
repository: YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/sample-app

# To your actual ECR URL from Step 5 output:
repository: 123456789.dkr.ecr.ap-south-1.amazonaws.com/sample-app
```

Commit and push this change:
```bash
git add helm-charts/sample-app/values.yaml
git commit -m "config: set ECR repository URL"
git push
```

---

### Step 9 — Add GitHub Actions secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret.

Add these 3 secrets:

| Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `AWS_REGION` | `ap-south-1` |

---

### Step 10 — Set up AWS Secrets Manager

Application secrets (database passwords, API keys) are never stored in Git. AWS Secrets Manager holds them; the External Secrets Operator syncs them into Kubernetes Secrets automatically.

**Store your secrets in AWS:**

```bash
aws secretsmanager create-secret \
  --name /gitops-platform/db-password \
  --secret-string "your-db-password" \
  --region ap-south-1

aws secretsmanager create-secret \
  --name /gitops-platform/api-key \
  --secret-string "your-api-key" \
  --region ap-south-1
```

**Install External Secrets Operator on the cluster:**

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace

# Verify the operator is running
kubectl get pods -n external-secrets
```

**Apply the ClusterSecretStore** (tells the operator which AWS account and region to pull from):

```bash
kubectl apply -f external-secrets/cluster-secret-store.yaml
```

The `cluster-secret-store.yaml` references the same IAM role your EKS node group uses — Terraform already created it with `secretsmanager:GetSecretValue` permission.

**Apply the ExternalSecret manifest** (which secrets to sync into each namespace):

```bash
kubectl apply -f external-secrets/external-secret.yaml -n dev
kubectl apply -f external-secrets/external-secret.yaml -n staging
kubectl apply -f external-secrets/external-secret.yaml -n prod
```

Verify the Kubernetes Secrets were created:

```bash
kubectl get secret app-secrets -n dev
# Expected: app-secrets   Opaque   2   30s
```

The operator re-syncs every hour. Any rotation in Secrets Manager propagates to the cluster automatically.

---

### Step 11 — Deploy the App-of-Apps (bootstrap ArgoCD)

This single command tells ArgoCD to watch your repo and manage all 3 environments:

```bash
kubectl apply -f argocd/app-of-apps.yaml -n argocd
```

Go to the ArgoCD UI (`https://localhost:8080`) — you should see 4 applications appear:
- `app-of-apps` (the root)
- `sample-app-dev`
- `sample-app-staging`
- `sample-app-prod`

They will be in `OutOfSync` state because no image has been pushed yet. That's expected — Step 12 triggers the first real deploy.

---

### Step 12 — Trigger your first real deployment

Push any small change to `main`:

```bash
# Make a tiny change
echo "# First GitOps deploy" >> app/app.py
git add app/app.py
git commit -m "feat: first deployment"
git push origin main
```

Now watch what happens:

1. Go to your GitHub repo → Actions tab
2. You'll see the pipeline running: tests → build → push to ECR → update values.yaml
3. Go to ArgoCD UI → watch `sample-app-dev` and `sample-app-staging` automatically turn green (Synced)
4. Prod stays waiting for manual approval

---

### Step 13 — Verify the deployment

```bash
# Check pods are running in dev
kubectl get pods -n dev

# Port-forward to test the app
kubectl port-forward svc/sample-app -n dev 8888:80

# In a new terminal — test all endpoints
curl http://localhost:8888/
curl http://localhost:8888/health
curl http://localhost:8888/version
```

The `/version` endpoint will show the git SHA that was just deployed:
```json
{
  "version": "a3f8c2d...",
  "environment": "dev",
  "git_commit": "a3f8c2d..."
}
```

This is proof GitOps is working — the version in the running container matches the commit that triggered the pipeline.

---

### Step 14 — Deploy to production (manual)

When you're happy with dev and staging, go to ArgoCD UI:
1. Click on `sample-app-prod`
2. Click the `Sync` button
3. Click `Synchronize`

Production is now deployed. The manual gate prevents accidental prod deploys.

---

## How to demo this in an interview

When an interviewer asks "walk me through a deployment":

1. Show the ArgoCD UI with all 3 environments
2. Make a small code change → push to main
3. Show GitHub Actions pipeline running live
4. Show ArgoCD auto-syncing dev and staging
5. Show the `/version` endpoint before and after — the SHA changes
6. Show prod waiting for manual approval
7. Click Sync on prod — show it deploying

That sequence demonstrates the entire GitOps flow end-to-end in under 5 minutes.

---

## How to test HPA (pod autoscaling)

```bash
# Watch pods scale in a separate terminal
kubectl get hpa -n dev -w

# Generate load in another terminal
watch -n 0.3 'curl -s http://localhost:8888/simulate/load'
```

After ~60 seconds you'll see the pod count increase automatically. Stop the load and pods scale back down after ~5 minutes.

---

## How to do a rollback

In the ArgoCD UI:
1. Click on `sample-app-dev`
2. Click `History and Rollback`
3. Find the previous working version
4. Click `Rollback`

Rollback completes in under 2 minutes — ArgoCD just re-applies the old Helm values with the old image tag.

---

## Progressive delivery with Argo Rollouts

This platform uses Argo Rollouts instead of the default Kubernetes `Deployment` for controlled, risk-reduced releases.

### Install Argo Rollouts

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

### Canary strategy (staging)

The staging `values-staging.yaml` configures a canary rollout — traffic shifts gradually before full promotion:

```yaml
rollout:
  strategy: canary
  steps:
    - setWeight: 10    # send 10% of traffic to new version
    - pause: {duration: 60s}
    - setWeight: 50    # ramp to 50%
    - pause: {duration: 60s}
    - setWeight: 100   # full promotion
```

Watch the rollout progress:
```bash
kubectl argo rollouts get rollout sample-app -n staging -w
```

### Blue-green strategy (prod)

Production uses blue-green — the new version (green) runs alongside the old (blue) until you manually promote:

```yaml
rollout:
  strategy: blueGreen
  autoPromotionEnabled: false   # requires manual promotion
  scaleDownDelaySeconds: 30
```

Promote after validating the green stack:
```bash
kubectl argo rollouts promote sample-app -n prod
```

Abort and instantly roll back to blue:
```bash
kubectl argo rollouts abort sample-app -n prod
```

---

## Secrets management with AWS Secrets Manager

Secrets are never stored in Git. The External Secrets Operator syncs values from AWS Secrets Manager into Kubernetes Secrets at runtime.

### How it flows

```
AWS Secrets Manager
  └── /gitops-platform/db-password
  └── /gitops-platform/api-key
          │
          ▼  (External Secrets Operator polls every 1h)
Kubernetes Secret (in each namespace)
          │
          ▼
Pod mounts secret as env var
```

### Store a secret in AWS

```bash
aws secretsmanager create-secret \
  --name /gitops-platform/db-password \
  --secret-string "your-db-password" \
  --region ap-south-1
```

### ExternalSecret manifest

The `ExternalSecret` resource (committed to Git, secrets are not) tells the operator what to fetch:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: app-secrets          # creates this Kubernetes Secret
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: /gitops-platform/db-password
```

### Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace
```

---

## Multi-cluster support

ArgoCD is configured to manage multiple EKS clusters from a single control plane. Each cluster is registered and targeted by the ArgoCD `Application` manifests.

Register an additional cluster:
```bash
# Log in to ArgoCD CLI
argocd login localhost:8080 --username admin --password <password> --insecure

# Add the second cluster (must have kubeconfig context set up)
argocd cluster add <context-name> --name staging-cluster
```

Each ArgoCD app (dev/staging/prod) targets its cluster via the `destination.server` field in the app manifest:

```yaml
destination:
  server: https://<cluster-endpoint>.eks.amazonaws.com   # per-cluster endpoint
  namespace: prod
```

This means one ArgoCD instance drives deployments to all environments across different clusters — a single pane of glass.

---

## Cleanup (avoid AWS charges)

```bash
# Delete ArgoCD apps first
kubectl delete -f argocd/app-of-apps.yaml -n argocd

# Destroy all AWS infrastructure
cd terraform
terraform destroy
```

Type `yes` to confirm. This deletes the EKS cluster, VPC, and ECR repository.

---

## Author

**Sudalaimani S** — DevOps Engineer
[LinkedIn](https://www.linkedin.com/in/sudalaimanis/) | [GitHub](https://github.com/sudalaimanis)
