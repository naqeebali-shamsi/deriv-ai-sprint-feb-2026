---
title: Demo Hosting Guide (AWS Lightsail + LLM)
status: Current
date: 2026-02-07
---

# Demo Hosting Guide (AWS Lightsail + LLM)

Purpose: Deploy the demo stack with an **LLM runtime** so judges can access from their devices.

## Summary (Current Live Host)

- Provider: AWS Lightsail
- Instance name: `deriv-demo-xlarge`
- Region/AZ: `us-east-1a`
- Public IP: `44.215.67.132`
- UI: `http://44.215.67.132:8501`
- API: `http://44.215.67.132:8000`
- Model: `llama3.1:8b` (Ollama, internal only — not exposed publicly)

Note: Replace the IP if the instance is recreated. Consider attaching a static IP.

## Security Notes (Demo-Only)

- **No HTTPS** — all traffic is plaintext. Acceptable for hackathon demo on local network.
- **No authentication** — all endpoints are open. Do not expose to public internet beyond demo.
- **Ollama is internal-only** — accessible by backend via Docker network, not exposed on public ports.
- **CORS is wildcard** — `CORS_ORIGINS=*` for demo convenience.

## Prerequisites

- AWS CLI configured with credentials.
- Local SSH key: Lightsail default key pair for `us-east-1`.
- Repo contains `docker-compose.yml` with Ollama services.

## Ports (Public)

Open on the instance:
- `22/tcp` (SSH)
- `8000/tcp` (FastAPI)
- `8501/tcp` (Streamlit)

Ollama (11434) is **not** exposed publicly — backend accesses it via Docker internal network.

## Deployment Steps (CLI)

### 1) Create Lightsail instance (xlarge)

```
aws lightsail create-instances \
  --region us-east-1 \
  --instance-names deriv-demo-xlarge \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id xlarge_3_0
```

Get IP:
```
aws lightsail get-instance \
  --region us-east-1 \
  --instance-name deriv-demo-xlarge \
  --query "instance.publicIpAddress"
```

Open ports:
```
aws lightsail open-instance-public-ports \
  --region us-east-1 \
  --instance-name deriv-demo-xlarge \
  --port-info fromPort=8000,toPort=8000,protocol=TCP

aws lightsail open-instance-public-ports \
  --region us-east-1 \
  --instance-name deriv-demo-xlarge \
  --port-info fromPort=8501,toPort=8501,protocol=TCP
```

(Optional) Attach a static IP to prevent IP changes on reboot:
```
aws lightsail allocate-static-ip --static-ip-name deriv-demo-ip
aws lightsail attach-static-ip \
  --static-ip-name deriv-demo-ip \
  --instance-name deriv-demo-xlarge
```

### 2) Install Docker Compose v2 on the instance

```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "sudo apt-get update -y && sudo apt-get install -y docker.io curl git"
```

Install Docker Compose v2 plugin:
```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "sudo mkdir -p /usr/local/lib/docker/cli-plugins && \
   sudo curl -sSL https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-linux-x86_64 \
   -o /usr/local/lib/docker/cli-plugins/docker-compose && \
   sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose"
```

### 3) Upload project

```
scp -i "<path_to_lightsail_key>.pem" -r \
  backend risk patterns sim ui scripts schemas models \
  Dockerfile docker-compose.yml requirements.txt pyproject.toml \
  config.py .env.example \
  ubuntu@<PUBLIC_IP>:~/DERIV_AI_HACKATHON
```

### 4) Configure environment

```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && cp .env.example .env"
```

The `.env.example` defaults are correct for Docker Compose (OLLAMA_URL points to internal Docker network). Edit `.env` only if you need to override defaults.

### 5) Start stack with LLM

Run setup profile first (initializes DB, pulls LLM model, bootstraps ML model, seeds demo data):
```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && sudo docker compose --profile setup up --build"
```

Wait for setup services to complete, then start the main stack:
```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && sudo docker compose up -d --build"
```

### 6) Verify

```
curl -s http://<PUBLIC_IP>:8000/health
curl -s http://<PUBLIC_IP>:8501
```

Check model is present:
```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && sudo docker compose exec ollama ollama list"
```

Check all containers healthy:
```
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && sudo docker compose ps"
```

## Notes / Warnings

- **Do not commit private keys** or store them in the repo (`.gitignore` and `.dockerignore` exclude `*.pem`).
- Model download is large (~5 GB) and can take a few minutes.
- Lightsail costs scale with bundle size; shut down when done.
- The xlarge instance (16 GB RAM) is sufficient but monitor memory if running long sessions.

## Redeployment (Code Update)

Since the app is deployed via SCP (no git on server), redeploy by re-uploading and rebuilding:
```
# Re-upload changed files
scp -i "<path_to_lightsail_key>.pem" -r \
  backend risk patterns sim ui scripts schemas models \
  Dockerfile docker-compose.yml requirements.txt config.py \
  ubuntu@<PUBLIC_IP>:~/DERIV_AI_HACKATHON

# Rebuild and restart
ssh -i "<path_to_lightsail_key>.pem" ubuntu@<PUBLIC_IP> \
  "cd ~/DERIV_AI_HACKATHON && sudo docker compose up -d --build"
```

## Cleanup (After Demo)

Stop and remove instance:
```
aws lightsail delete-instance --region us-east-1 --instance-name deriv-demo-xlarge
```

Release any static IPs if attached:
```
aws lightsail release-static-ip --static-ip-name deriv-demo-ip
```
