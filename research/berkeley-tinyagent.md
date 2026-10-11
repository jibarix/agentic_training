# TinyAgent: Function Calling at the Edge (Berkeley BAIR Blog, May 29, 2024)

- **URL:** https://bair.berkeley.edu/blog/2024/05/29/tiny-agent/
- **Authors:** Lutfi Eren Erdogan, Nicholas Lee, Siddharth Jha, Sehoon Kim, Ryan Tabrizi, Suhong Moon, Coleman Hooper, Gopala Anumanchipalli, Kurt Keutzer, Amir Gholami (UC Berkeley, SqueezeAILab)
- **Paper:** "TinyAgent: Function Calling at the Edge," EMNLP 2024 Demo, https://arxiv.org/abs/2409.00608
- **Code:** https://github.com/SqueezeAILab/TinyAgent (MIT license)
- **Models and data (Hugging Face):** https://huggingface.co/squeeze-ai-lab/TinyAgent-1.1B, https://huggingface.co/squeeze-ai-lab/TinyAgent-1.1B-GGUF, https://huggingface.co/squeeze-ai-lab/TinyAgent-7B, https://huggingface.co/squeeze-ai-lab/TinyAgent-7B-GGUF, https://huggingface.co/squeeze-ai-lab/TinyAgent-ToolRAG, https://huggingface.co/datasets/squeeze-ai-lab/TinyAgent-dataset
- **Demo video:** https://youtu.be/0GvaGL9IDpQ
- **Tags:** TOOL, TRAIN, DEPLOY

## Summary

TinyAgent asks whether a small language model (1-7B) can match the function-calling and planning ability of large cloud LLMs while running fully on-device, which brings privacy, offline use, and lower latency. The target is a Siri-like macOS assistant that turns natural-language commands into calls over 16 functions (Email, Contacts, SMS, Calendar, Notes, Reminders, file management, Zoom, Maps), each backed by an AppleScript. Instead of answering from parametric knowledge, the model emits an LLMCompiler-style plan, a DAG of function calls with arguments and dependencies, which is parsed and executed in dependency order. Off-the-shelf small models (TinyLlama-1.1B, Wizard-2-7B) produced broken plans: wrong or hallucinated functions, bad dependencies, and broken syntax. After targeted fine-tuning, the small models beat GPT-4-Turbo.

## Key techniques

1. **LLMCompiler planning.** The model outputs a parallelizable function-calling plan (a DAG) rather than sequential ReAct steps. See https://arxiv.org/pdf/2312.04511 and https://github.com/SqueezeAILab/LLMCompiler.
2. **Synthetic data generation.** GPT-4-Turbo generated realistic queries with plans and arguments from sampled function sets. Sanity checks confirmed that each graph is feasible and that function names and argument types are valid. The result was about 80K train, 1K val, and 1K test examples for roughly $500. (The repo README describes the HF dataset as 40,000 use cases, a discrepancy.)
3. **LoRA fine-tuning.** 3 epochs at lr 7e-5. Training prompts mix the ground-truth functions with irrelevant "negative" functions so the model learns tool selection, and they include retrieved in-context examples.
4. **Evaluation by graph isomorphism.** A plan scores 1 only if its DAG is isomorphic to the ground truth with correct functions.
5. **Tool RAG as a classifier.** Embedding-similarity retrieval missed auxiliary tools (e.g. `get_email_address` for a calendar invite). The authors instead fine-tuned DeBERTa-v3-small as a 16-way multi-label classifier (threshold 0.5), which selects about 3.97 tools per query at 0.998 recall. This cut the prompt from 2,762 to 1,397 tokens and also raised accuracy.
6. **Quantization for the edge.** 4-bit weights (group size 32) for llama.cpp, with quantization-aware training. Accuracy held and latency dropped.
7. **Local voice input.** Whisper-v3 runs via whisper.cpp.

**Results (success rate / latency / size):** GPT-3.5 65.04% / 3.2 s. GPT-4-Turbo 79.08% / 3.9 s. TinyAgent-1.1B 4-bit 80.35% / 2.9 s / 0.68 GB. TinyAgent-7B 4-bit 85.14% / 13.1 s / 4.37 GB. Fine-tuning alone raised the 1.1B model from 12.71% to 78.89% and the 7B from 41.25% to 83.09%. Everything runs locally on a MacBook Pro M3.

## What a learner should take away

- Function calling is a narrow, learnable skill. A 1.1B model trained on about 80K high-quality synthetic examples can beat a frontier model within a fixed toolset, though it does not generalize to new tools. The repo notes that custom tools only work with GPT models.
- Distilling from a strong model through synthetic data, validated programmatically, is a cheap and repeatable recipe for specializing agents.
- Tool selection is its own retrieval problem. A small classifier can beat embedding RAG, and shorter prompts improve both latency and accuracy.
- Planning as a DAG (LLMCompiler) enables parallel tool execution and gives a precise evaluation target (graph isomorphism).
- Deployment levers include quantization, quantization-aware training, llama.cpp/GGUF, and local ASR. Together they make private, offline agents practical.

## Suggested place in a learning path

Read after the basics of tool use and function calling (e.g. CMU 11-768 Lecture 2) and an introduction to fine-tuning/SFT (e.g. CMU 11-768 Lecture 8). It works as a case study bridging TOOL, TRAIN, and DEPLOY: small-model distillation for agents, tool retrieval, and edge deployment. A good follow-up project is to fine-tune a small model on synthetic function-calling data for a custom toolset and compare it against a frontier API on accuracy, latency, and cost.

## Related references cited in the post

- LLMCompiler: https://arxiv.org/pdf/2312.04511
- Toolformer: https://arxiv.org/pdf/2302.04761
- Gorilla: https://arxiv.org/pdf/2305.15334
- LLM2LLM: https://arxiv.org/pdf/2403.15042
- Self-Instruct: https://arxiv.org/pdf/2212.10560
- Quantization survey: https://arxiv.org/pdf/2103.13630
- llama.cpp: https://github.com/ggerganov/llama.cpp ; whisper.cpp: https://github.com/ggerganov/whisper.cpp

## Notes

- The blog and the repo loaded fully. The post's Table 1 lists basic RAG as "top 3, 0.949 recall," while the text says top-6 at 0.968 recall. The two are inconsistent in the source.
