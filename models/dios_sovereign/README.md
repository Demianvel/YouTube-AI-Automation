# DHH Sovereign v1

`DHH Sovereign v1` is the local/offline media runtime for the `dioshablahoyia` channel.

It is designed to remove per-generation AI-credit dependencies from the media pipeline. GitHub stores the code, configuration, training scripts and small adapters; the heavy model weights should live on a self-hosted runner or in Git LFS / a private release asset under the applicable upstream model licenses.

## Important identity note

The visual character is an **artistic, photorealistic depiction of Jesus**, guided by the repository reference bank. It is not claimed to be a historically verified photograph or the objectively true appearance of God or Jesus.

The zero-credit local voice is called **Voz de Luz Local**. It is intentionally a distinct local voice. It must never be labelled as `Algenib`. Exact `Algenib` remains a Gemini TTS voice and therefore cannot honestly be represented as a fully local model.

## Directory layout

```text
models/dios_sovereign/
  image/
    base/                           # local Diffusers-compatible base model directory
    lora/
      dios_jesus_identity.safetensors
  voice/
    voz_de_luz_local.onnx          # Piper-compatible neural voice
    voz_de_luz_local.onnx.json
```

The runtime refuses remote downloads by setting `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `DIFFUSERS_OFFLINE=1`.

## Image modes

1. **Local diffusion + channel LoRA**: preferred professional mode when a local Diffusers-compatible base model and the identity LoRA are installed.
2. **Direct reference cinematic mode**: zero-credit fallback using only `jesus_reference_a.jpg`, `jesus_reference_b.jpg` and `jesus_reference_c.jpg`. It preserves the established visual identity and applies cinematic framing/motion without inventing a new face.

No Hugging Face inference endpoint, ZeroGPU space, Gemini image generation, Pexels or Pollinations is required by this runtime.

## Voice mode

Production zero-credit voice requires a local Piper-compatible Spanish neural voice file. The repository runtime performs local mastering with ffmpeg after synthesis. There is deliberately no espeak fallback in production mode because a low-quality emergency voice should not silently replace the channel identity.

## Training the visual identity LoRA

Use `scripts/dios_sovereign_prepare_dataset.py` to build an augmented training set from the approved reference bank and `scripts/dios_sovereign_train_lora.py` on a Linux machine with an NVIDIA GPU.

A self-hosted GPU runner is the practical zero-credit production path. Standard GitHub-hosted CPU runners are suitable for validation and the direct-reference fallback, but not for consistently fast high-quality diffusion generation.

## Publication policy

The sovereign runtime is intended to preserve the channel rules:

- 10 Shorts per Argentina calendar day.
- 2 long-form videos per weekend.
- local biblical editorial engine with anti-repeat history.
- no silent voice substitution.
- no remote AI inference credits in sovereign mode.

YouTube upload itself still uses the YouTube API/OAuth token and therefore remains a network operation separate from media generation.
