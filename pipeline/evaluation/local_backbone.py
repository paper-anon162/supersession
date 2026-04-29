"""Local HuggingFace backbones for the LLM judge and other LLM-driven steps.

Two backbones:

  - ``HFTransformersJudgeBackbone``  — generic transformers ``AutoModelForCausalLM``
                                       loader. Works with FP16 / BF16 / GPTQ /
                                       AWQ models depending on what's installed.

  - ``HFTransformersBackbone``       — same loader, exposed as a callable for
                                       wrapper extraction / surface realization
                                       prompts (i.e. anything that needs a
                                       free-form completion).

Both backbones lazy-load the model so importing this module is cheap. The
first call materializes the model; subsequent calls reuse the loaded handle.

Usage::

    from pipeline.evaluation.local_backbone import HFTransformersJudgeBackbone
    judge = HFTransformersJudgeBackbone(
        model_id="Qwen/Qwen2.5-7B-Instruct-AWQ",
        max_new_tokens=400,
    )
    verdict = judge_sample(sample, response, judge)

Phase 0 ships a ``HeuristicJudgeBackbone`` stub; this module is the bridge
to a real LLM judge once a local model is provisioned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# transformers / torch are imported lazily so the rest of the pipeline does
# not pull a 1.5 GB import path every time something touches the schema.


@dataclass
class HFTransformersBackbone:
    """Plain text-completion backbone."""

    model_id: str
    max_new_tokens: int = 512
    temperature: float = 0.0
    name: str = ""
    dtype: str = "auto"  # "auto" / "float16" / "bfloat16"
    device_map: str = "auto"
    system_prompt: str | None = None
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.model_id.replace("/", "__")

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        dtype_map = {
            "auto": "auto",
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        torch_dtype = dtype_map.get(self.dtype, "auto")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch_dtype,
            device_map=self.device_map,
        )
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token_id = self._tokenizer.eos_token_id

    def __call__(self, prompt: str) -> str:
        self._load()
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)
        gen_kwargs = dict(
            max_new_tokens=self.max_new_tokens,
            do_sample=self.temperature > 0,
            pad_token_id=self._tokenizer.pad_token_id,
        )
        if self.temperature > 0:
            gen_kwargs["temperature"] = self.temperature
        output_ids = self._model.generate(**inputs, **gen_kwargs)
        new_tokens = output_ids[0, inputs["input_ids"].shape[-1]:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


@dataclass
class HFTransformersJudgeBackbone(HFTransformersBackbone):
    """Same loader, configured for the judge prompt.

    The judge prompt already contains the full instructions (see
    ``prompts/judge_vf.jinja``); we override ``system_prompt`` to None so the
    rendered prompt is passed verbatim as the user message.
    """

    name: str = "hf_judge"

    def __post_init__(self) -> None:
        super().__post_init__()
        # Judge expects strict-JSON output; lock to deterministic decoding.
        self.temperature = 0.0
        if not self.system_prompt:
            self.system_prompt = None


__all__ = [
    "HFTransformersBackbone",
    "HFTransformersJudgeBackbone",
]
