# Hybrid Edge-Cloud LLM Routing Pipeline

A cross-platform, production-ready hybrid AI architecture that distributes workloads intelligently between a containerized cloud gateway and an OS-aware edge inference node. The system safely intercepts public traffic, parses runtime parameters, and routes prompts down an encrypted tunnel to specialized, low-rank adapted (LoRA) model lobes optimized natively for the host's underlying hardware accelerator.

---

## Core Architecture & Features

This project addresses standard corporate data-privacy limitations and edge-memory bottlenecks via a decoupled design pattern:

- **Cloud Orchestration Layer:** A lightweight, containerized FastAPI application ready for cloud deployment. It manages API credential validation, client-facing request schema checking, and rolling sliding-window rate limiting.
- **Encrypted Tunneling Connection:** Leverages Cloudflare Tunnels to pipe inbound gateway data straight to local hardware. This setup removes the security liability of opening inbound router ports or exposing static residential public IP addresses.
- **Dual-Engine Hardware Router:** An intelligent inference worker script detects the execution environment at startup. It maps requests natively through **Apple Silicon Metal (MLX)** if run on a Mac, or leverages **NVIDIA CUDA (Unsloth)** if run on Windows/Linux.
- **Asymmetric LoRA Lobe Specialization:** Rather than deploying a monolithic fine-tuned checkpoint, the system mounts task-specific adapters to a single 4-bit base model (`Qwen/Qwen2.5-7B-Instruct`).
  - **Text Generation Adapter (r=16, α=16):** Fine-tuned for rapid instruction following and conversational workflows.
  - **Reasoning Lobe (r=32, α=32):** Higher-rank allocation dedicated to step-by-step mathematical reasoning and chain-of-thought calculation patterns.

---

## Repository Layout

```text
llm-routing-pipeline/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                 # Automation workflow for code quality check
│
├── training/                         # Cloud-Based Training & Data Synthesis Layer
│   ├── data/
│   │   ├── raw/                      # Target folder for raw public text downloads
│   │   └── cleaned/                  # Extracted JSONL data formatted to conversation templates
│   └── notebooks/
│       ├── 01_data_cleaning.ipynb    # Automates data scraping and ShareGPT conversion
│       ├── 02_finetune_text.ipynb    # Unsloth notebook for standard instruction LoRA
│       └── 03_finetune_reason.ipynb  # Unsloth notebook for multi-step reasoning LoRA
│
├── inference_worker/                 # Cross-Platform Local Edge Node
│   ├── adapters/
│   │   ├── text_gen_lora_adapter/    # Config matrices and safetensors for instruction tasks
│   │   └── reasoning_lora_adapter/   # Config matrices and safetensors for reasoning tasks
│   ├── local_server.py               # OS-Aware FastAPI server (MLX-LM vs Unsloth selection)
│   └── requirements.txt              # Cross-platform edge engine dependencies
│
├── api_gateway/                      # Cloud Ingestion Proxy Layer
│   ├── Dockerfile                    # Containerization configuration blueprint
│   ├── requirements.txt              # Cloud proxy software packages
│   └── app/
│       ├── main.py                   # Global system server configuration entrypoint
│       ├── api/
│       │   └── routes.py             # Validates keys and handles proxy forwarding
│       ├── core/
│       │   ├── config.py             # Parses environment states securely
│       │   └── security.py           # Sliding-window rate limiting calculations
│       └── services/
│           └── llm_client.py         # Routes async requests forward via tunnel
│
├── docker-compose.yml                # Controls building and local execution of the cloud gateway
├── .env.example                      # Template outlining required security variable keys
├── .gitignore                        # Standard protection schemas avoiding credential leakage
└── README.md                         # Architecture reference documentation
```

---

## Hardware & Software Configuration Details

The engine utilizes specific runtime parameters to run 7B parameter models safely on 8GB memory constraints without triggering Out-Of-Memory (OOM) faults.

- **Quantization:** Base models are loaded in strict 4-bit precision, reducing the standard weight footprint from roughly 14GB to approximately 5.5GB.
- **Memory Optimization:** Training uses the `adamw_8bit` optimizer together with gradient accumulation to reduce peak memory consumption.
- **Hardware Fallbacks:** On macOS, `mlx-lm` leverages Apple's unified memory architecture. On CUDA-capable systems, Unsloth injects optimized fused kernels for significantly faster inference.

---

## Step-by-Step Pipeline Execution Guide

To execute this distributed architecture, start the components from the bottom up.

### 1. Fine-Tuning Step (Pre-requisite)

1. Run the notebooks inside `training/notebooks/` using an NVIDIA-enabled environment (e.g., Google Colab).
2. Execute `01_data_cleaning.ipynb` to download and convert datasets into ShareGPT conversation format.
3. Train both LoRA adapters by running:
   - `02_finetune_text.ipynb`
   - `03_finetune_reason.ipynb`
4. Download the generated adapter weights and place them into:

```text
inference_worker/adapters/text_gen_lora_adapter/
inference_worker/adapters/reasoning_lora_adapter/
```

---

### 2. Launch the Local Inference Node (Terminal 1)

```bash
cd inference_worker

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python3 -m uvicorn local_server:app --host 0.0.0.0 --port 8000
```

> **Verification:** Open `http://localhost:8000/docs` to access the automatically generated Swagger UI and verify the `/v1/execute` endpoint.

---

### 3. Activate the Encrypted Tunnel (Terminal 2)

```bash
cloudflared tunnel --url http://localhost:8000
```

Expected output:

```text
+------------------------------------------------------------+
| Your quick tunnel has been created! Visit it at:           |
| https://your-random-subdomain.trycloudflare.com            |
+------------------------------------------------------------+
```

Copy the generated `.trycloudflare.com` URL.

---

### 4. Deploy the API Gateway (Terminal 3)

Create your environment file:

```bash
cp .env.example .env
```

Update `.env`:

```text
VALID_API_KEYS=sk-portfolio-token-value
EDGE_WORKER_URL=https://your-random-subdomain.trycloudflare.com/v1/execute
```

Build and start the gateway:

```bash
docker-compose up --build
```

---

## Validation & Usage

Once all services are running, send requests to the gateway exposed on **port 8080**.

### Text Generation Request

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "X-API-Key: sk-portfolio-token-value" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Compose a brief tagline for a secure software engineering platform.",
    "intent": "text"
  }'
```

---

### Mathematical Reasoning Request

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "X-API-Key: sk-portfolio-token-value" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Find the next item in the logical mathematical series: 2, 4, 8, 16...",
    "intent": "reason"
  }'
```

---

### Example Response

```json
{
  "active_lobe": "reason",
  "engine_used": "Apple MLX",
  "response": "1. Analyze the pattern: each number doubles the previous term.\n2. Compute: 16 × 2 = 32.\nThe next value in the series is 32."
}
```

---
