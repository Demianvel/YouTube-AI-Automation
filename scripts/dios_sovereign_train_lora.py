from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
import torch.nn.functional as F
from accelerate import Accelerator
from peft import LoraConfig
from peft.utils import get_peft_model_state_dict
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from transformers import CLIPTextModel, CLIPTextModelWithProjection, CLIPTokenizer

from diffusers import AutoencoderKL, DDPMScheduler, StableDiffusionXLPipeline, UNet2DConditionModel


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "models" / "dios_sovereign" / "image" / "base"
DEFAULT_DATA = ROOT / "models" / "dios_sovereign" / "training" / "jesus_identity"
DEFAULT_OUT = ROOT / "models" / "dios_sovereign" / "image" / "lora" / "dios_jesus_identity.safetensors"


class JsonlImageDataset(Dataset):
    def __init__(self, root: Path, resolution: int):
        self.root = root
        metadata = root / "metadata.jsonl"
        if not metadata.exists():
            raise RuntimeError(f"Falta {metadata}; ejecutar primero dios_sovereign_prepare_dataset.py")
        self.rows = [json.loads(line) for line in metadata.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(self.rows) < 24:
            raise RuntimeError("Dataset demasiado pequeno para entrenamiento estable.")
        self.transform = transforms.Compose(
            [
                transforms.Resize((resolution, resolution), interpolation=transforms.InterpolationMode.BICUBIC),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ]
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        row = self.rows[index]
        path = self.root / row["file_name"]
        with Image.open(path) as opened:
            image = opened.convert("RGB")
            pixel_values = self.transform(image)
        return {"pixel_values": pixel_values, "text": row["text"]}


def _encode_prompt(
    captions: list[str],
    tokenizer_one,
    tokenizer_two,
    text_encoder_one,
    text_encoder_two,
    device,
):
    prompt_embeds_list = []
    pooled = None
    for tokenizer, encoder in ((tokenizer_one, text_encoder_one), (tokenizer_two, text_encoder_two)):
        tokens = tokenizer(
            captions,
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        ).input_ids.to(device)
        outputs = encoder(tokens, output_hidden_states=True)
        pooled = outputs[0]
        prompt_embeds_list.append(outputs.hidden_states[-2])
    prompt_embeds = torch.cat(prompt_embeds_list, dim=-1)
    return prompt_embeds, pooled


def train(args) -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["DIFFUSERS_OFFLINE"] = "1"

    base = Path(args.base_model)
    data = Path(args.dataset)
    output = Path(args.output)
    if not base.exists():
        raise RuntimeError(f"Falta el modelo base local: {base}")

    accelerator = Accelerator(
        gradient_accumulation_steps=args.gradient_accumulation,
        mixed_precision=args.mixed_precision,
    )
    weight_dtype = torch.float16 if accelerator.mixed_precision == "fp16" else torch.bfloat16 if accelerator.mixed_precision == "bf16" else torch.float32

    tokenizer_one = CLIPTokenizer.from_pretrained(str(base), subfolder="tokenizer", local_files_only=True)
    tokenizer_two = CLIPTokenizer.from_pretrained(str(base), subfolder="tokenizer_2", local_files_only=True)
    text_encoder_one = CLIPTextModel.from_pretrained(str(base), subfolder="text_encoder", local_files_only=True)
    text_encoder_two = CLIPTextModelWithProjection.from_pretrained(str(base), subfolder="text_encoder_2", local_files_only=True)
    vae = AutoencoderKL.from_pretrained(str(base), subfolder="vae", local_files_only=True)
    unet = UNet2DConditionModel.from_pretrained(str(base), subfolder="unet", local_files_only=True)
    noise_scheduler = DDPMScheduler.from_pretrained(str(base), subfolder="scheduler", local_files_only=True)

    vae.requires_grad_(False)
    text_encoder_one.requires_grad_(False)
    text_encoder_two.requires_grad_(False)
    unet.requires_grad_(False)

    lora_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank,
        init_lora_weights="gaussian",
        target_modules=["to_k", "to_q", "to_v", "to_out.0"],
    )
    unet.add_adapter(lora_config)

    vae.to(accelerator.device, dtype=torch.float32)
    text_encoder_one.to(accelerator.device, dtype=weight_dtype)
    text_encoder_two.to(accelerator.device, dtype=weight_dtype)

    trainable = [p for p in unet.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.learning_rate, betas=(0.9, 0.999), weight_decay=1e-2, eps=1e-8)

    dataset = JsonlImageDataset(data, args.resolution)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=2, drop_last=True)
    unet, optimizer, dataloader = accelerator.prepare(unet, optimizer, dataloader)

    unet.train()
    global_step = 0
    while global_step < args.max_steps:
        for batch in dataloader:
            with accelerator.accumulate(unet):
                pixel_values = batch["pixel_values"].to(accelerator.device, dtype=torch.float32)
                with torch.no_grad():
                    latents = vae.encode(pixel_values).latent_dist.sample() * vae.config.scaling_factor
                    latents = latents.to(dtype=weight_dtype)
                    prompt_embeds, pooled = _encode_prompt(
                        list(batch["text"]),
                        tokenizer_one,
                        tokenizer_two,
                        text_encoder_one,
                        text_encoder_two,
                        accelerator.device,
                    )
                    prompt_embeds = prompt_embeds.to(dtype=weight_dtype)
                    pooled = pooled.to(dtype=weight_dtype)

                noise = torch.randn_like(latents)
                timesteps = torch.randint(
                    0,
                    noise_scheduler.config.num_train_timesteps,
                    (latents.shape[0],),
                    device=latents.device,
                ).long()
                noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)
                size = args.resolution
                time_ids = torch.tensor(
                    [[size, size, 0, 0, size, size]],
                    device=latents.device,
                    dtype=weight_dtype,
                ).repeat(latents.shape[0], 1)

                model_pred = unet(
                    noisy_latents,
                    timesteps,
                    encoder_hidden_states=prompt_embeds,
                    added_cond_kwargs={"text_embeds": pooled, "time_ids": time_ids},
                ).sample

                if noise_scheduler.config.prediction_type == "v_prediction":
                    target = noise_scheduler.get_velocity(latents, noise, timesteps)
                else:
                    target = noise
                loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")

                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

            if accelerator.sync_gradients:
                global_step += 1
                if accelerator.is_main_process and (global_step == 1 or global_step % 25 == 0):
                    print(f"step={global_step}/{args.max_steps} loss={loss.detach().item():.6f}")
                if global_step >= args.max_steps:
                    break

    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        unwrapped = accelerator.unwrap_model(unet)
        state = get_peft_model_state_dict(unwrapped)
        state = {f"unet.{key}": value.detach().cpu() for key, value in state.items()}
        output.parent.mkdir(parents=True, exist_ok=True)
        StableDiffusionXLPipeline.save_lora_weights(
            str(output.parent),
            unet_lora_layers=state,
            weight_name=output.name,
            safe_serialization=True,
        )
        manifest = {
            "engine": "dhh-sovereign-v1",
            "base_model": str(base),
            "dataset": str(data),
            "output": str(output),
            "rank": args.rank,
            "steps": args.max_steps,
            "resolution": args.resolution,
            "learning_rate": args.learning_rate,
        }
        output.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline SDXL LoRA trainer for the DHH visual identity")
    parser.add_argument("--base-model", default=str(DEFAULT_BASE))
    parser.add_argument("--dataset", default=str(DEFAULT_DATA))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--max-steps", type=int, default=700)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--mixed-precision", choices=["no", "fp16", "bf16"], default="fp16")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
