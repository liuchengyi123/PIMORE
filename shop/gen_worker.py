"""One process per GPU. The shop posts the reference photo; this process redraws it.

Start on each 4090:

    GEN_TOKEN=... python -m shop.gen_worker

The shop stores that machine's http://host:8781 address. Four machines, four addresses.
"""

import base64
import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image

HOST = os.environ.get("GEN_HOST", "0.0.0.0")
PORT = int(os.environ.get("GEN_PORT", "8781"))
TOKEN = os.environ.get("GEN_TOKEN", "").strip()
STEPS = int(os.environ.get("GEN_STEPS", "4"))
DIFFSYNTH = os.environ.get("DIFFSYNTH_HOME", "/root/DiffSynth-Studio")
LOCAL_MODELS = os.environ.get("GEN_LOCAL_MODELS", "/root/autodl-tmp/models")
BASE_MODELS = os.environ.get("GEN_BASE_MODELS", "/root/qwen-image-edit-files/models")
LORA = os.environ.get(
    "GEN_LORA",
    "/root/autodl-tmp/models/fast/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
)

_pipe = None


def _multiple(value):
    value = int(value or 768)
    value = max(64, min(2048, value))
    return max(64, value // 64 * 64)


def pipeline():
    global _pipe
    if _pipe is None:
        import sys

        import torch

        if DIFFSYNTH not in sys.path:
            sys.path.insert(0, DIFFSYNTH)
        from diffsynth.pipelines.qwen_image import ModelConfig, QwenImagePipeline

        _pipe = QwenImagePipeline.from_pretrained(
            torch_dtype=torch.bfloat16,
            device="cuda",
            model_configs=[
                ModelConfig(
                    model_id="Qwen/Qwen-Image-Edit-2509",
                    origin_file_pattern="transformer/diffusion_pytorch_model*.safetensors",
                    local_model_path=LOCAL_MODELS,
                    offload_device="cpu",
                    skip_download=True,
                ),
                ModelConfig(
                    model_id="Qwen/Qwen-Image",
                    origin_file_pattern="text_encoder/model*.safetensors",
                    local_model_path=BASE_MODELS,
                    offload_device="cpu",
                    skip_download=True,
                ),
                ModelConfig(
                    model_id="Qwen/Qwen-Image",
                    origin_file_pattern="vae/diffusion_pytorch_model.safetensors",
                    local_model_path=BASE_MODELS,
                    skip_download=True,
                ),
            ],
            processor_config=ModelConfig(
                model_id="Qwen/Qwen-Image-Edit",
                origin_file_pattern="processor/",
                local_model_path=LOCAL_MODELS,
                skip_download=True,
            ),
            tokenizer_config=ModelConfig(
                model_id="Qwen/Qwen-Image",
                origin_file_pattern="tokenizer/",
                local_model_path=BASE_MODELS,
                skip_download=True,
            ),
        )
        _merge_lightning(_pipe.dit, LORA)
        _pipe.enable_vram_management()
    return _pipe


def _merge_lightning(module, path):
    import torch
    from diffsynth.models import load_state_dict

    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    state = load_state_dict(path, torch_dtype=torch.bfloat16, device="cpu")
    named = dict(module.named_modules())
    updated = 0
    for key, up in state.items():
        if not key.endswith(".lora_up.weight"):
            continue
        prefix = key[: -len(".lora_up.weight")]
        down = state[prefix + ".lora_down.weight"]
        if down.shape[0] != up.shape[1]:
            down = down.transpose(0, 1)
        alpha = state.get(prefix + ".alpha")
        scale = float(alpha.float().reshape(-1)[0]) / float(down.shape[0]) if alpha is not None else 1.0
        layer = named.get(prefix)
        if layer is None or not hasattr(layer, "weight"):
            continue
        weight = layer.weight.data
        delta = torch.mm(up.float(), down.float()) * scale
        merged = (weight.float() + delta.to(device=weight.device)).to(dtype=weight.dtype)
        layer.weight.data.copy_(merged)
        updated += 1
    if updated == 0:
        raise RuntimeError("4-step lora matched no layers")
    print("lightning tensors", updated, flush=True)


def redraw(data, prompt, width, height):
    image = Image.open(io.BytesIO(data)).convert("RGB")
    image.thumbnail((768, 768))
    result = pipeline()(
        prompt=prompt,
        edit_image=[image],
        num_inference_steps=STEPS,
        height=_multiple(height),
        width=_multiple(width),
        seed=1,
        cfg_scale=1,
        edit_image_auto_resize=True,
    )
    out = io.BytesIO()
    result.convert("RGB").save(out, format="JPEG", quality=90, subsampling=0)
    import torch
    torch.cuda.empty_cache()
    return out.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="text/plain; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?", 1)[0] != "/health":
            self._send(404, "not found")
            return
        self._send(200, "ok")

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/edit":
            self._send(404, "not found")
            return
        if TOKEN and self.headers.get("X-Gen-Token", "") != TOKEN:
            self._send(401, "token")
            return
        length = int(self.headers.get("Content-Length") or "0")
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            raw = base64.b64decode(payload.get("image_b64") or "")
            prompt = str(payload.get("prompt") or "").strip()
            width = int(payload.get("width") or 800)
            height = int(payload.get("height") or 800)
            if not raw or not prompt:
                raise ValueError("empty")
            jpeg = redraw(raw, prompt, width, height)
        except Exception:
            import traceback
            traceback.print_exc()
            self._send(500, "edit failed")
            return
        self._send(200, jpeg, "image/jpeg")

    def log_message(self, fmt, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
