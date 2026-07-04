import platform
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ==============================================================================
# 1. HARDWARE DETECTION & CONFIGURATION
# ==============================================================================
SYSTEM_OS = platform.system()
IS_MAC = SYSTEM_OS == "Darwin"

BASE_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct" if not IS_MAC else "mlx-community/Qwen2.5-7B-Instruct-4bit"

ADAPTER_PATHS = {
    "text": "./adapters/text_gen_lora_adapter",
    "reason": "./adapters/reasoning_lora_adapter"
}

app = FastAPI(
    title="Hybrid Edge LLM Router", 
    description="OS-Aware Inference Engine (MLX for Apple Silicon, Unsloth for NVIDIA)"
)

# Global State Memory
active_model = None
active_tokenizer = None
current_intent = None

# ==============================================================================
# 2. DUAL-ENGINE ORCHSTRATION (MLX vs UNSLOTH)
# ==============================================================================
def load_orchestration_layer(intent: str):
    global active_model, active_tokenizer, current_intent
    
    if current_intent == intent and active_model is not None:
        return active_model, active_tokenizer
        
    print(f"\n[RAM Management] Architecture Shift: Swapping to {intent.upper()} adapter.")
    adapter_path = ADAPTER_PATHS.get(intent)
    
    if IS_MAC:
        # ---------------------------------------------------------
        # APPLE SILICON ENGINE (Metal / MLX)
        # ---------------------------------------------------------
        from mlx_lm import load
        active_model, active_tokenizer = load(
            BASE_MODEL_ID,
            adapter_path=adapter_path
        )
    else:
        # ---------------------------------------------------------
        # NVIDIA ENGINE (CUDA / Unsloth)
        # ---------------------------------------------------------
        from unsloth import FastLanguageModel
        active_model, active_tokenizer = FastLanguageModel.from_pretrained(
            model_name=BASE_MODEL_ID,
            max_seq_length=2048,
            dtype=None,          # Auto-detects fp16/bf16
            load_in_4bit=True,   # Uses bitsandbytes natively
        )
        # Apply the specific LoRA intent
        active_model.load_adapter(adapter_path)
        # Enable 2x faster native Unsloth inference
        FastLanguageModel.for_inference(active_model) 

    current_intent = intent
    return active_model, active_tokenizer

# ==============================================================================
# 3. REQUEST SCHEMA & ENDPOINT
# ==============================================================================
class InferenceRequest(BaseModel):
    prompt: str
    intent: str
    max_tokens: int = 200

@app.post("/v1/execute")
def execute_inference(request: InferenceRequest):
    if request.intent not in ADAPTER_PATHS:
        raise HTTPException(status_code=400, detail="Invalid intent. Choose 'text' or 'reason'.")
        
    try:
        model, tokenizer = load_orchestration_layer(request.intent)
        
        if IS_MAC:
            # Apple MLX Generation Execution
            from mlx_lm import generate
            
            messages = [{"role": "user", "content": request.prompt}]
            formatted_prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            response_text = generate(
                model=model,
                tokenizer=tokenizer,
                prompt=formatted_prompt,
                max_tokens=request.max_tokens,
                verbose=False
            )
            
        else:
            # Unsloth / Hugging Face Generation Execution
            messages = [{"role": "user", "content": request.prompt}]
            inputs = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
            ).to("cuda")
            
            outputs = model.generate(
                input_ids=inputs, 
                max_new_tokens=request.max_tokens, 
                use_cache=True,
                pad_token_id=tokenizer.eos_token_id
            )
            
            # Decode the generated tokens (ignoring the input prompt)
            response_text = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

        return {
            "active_lobe": request.intent,
            "engine_used": "Apple MLX" if IS_MAC else "Unsloth CUDA",
            "response": response_text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))