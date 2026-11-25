# Local inference in ReidX

## Decision

Keep Ollama for memory embeddings and use the current Ollama setup as the CPU chat baseline. AirLLM is a candidate for occasional, asynchronous text work when the desired model cannot fit in memory. Its fit for the interactive terminal is unproven.

## What was verified

Safe and burst profiles can use the same Nomic embedding alias, model and Ollama endpoint. The gateway owns the alias-to-provider mapping, so an experiment can use a new alias without changing existing agent or memory identifiers.

The memory MCP prefixes inputs with Nomic's document or query task prefix and stores embeddings alongside its SQLite full-text index. Switching chat inference does not require re-embedding memory. If the embedding model changes, rebuild the stored vectors before comparing similarity scores.

## What AirLLM changes

AirLLM splits supported Transformers checkpoints into per-layer shards and loads weights as layers execute. Prefetching can overlap some transfer with compute, but decoding still revisits the layers for each token. Sharding adds a first-run operation and can require disk space for both the original checkpoint and the layer copies. AirLLM's model-fit headline describes GPU memory capacity. Transfer bandwidth, CPU compute, context length, checkpoint compatibility and disk cache behavior determine whether a given workload is practical. Optional compression may reduce weight transfers, but its speed and availability depend on the backend. The configured Ollama GGUF artifacts cannot be used as drop-in Transformers checkpoints. [AirLLM source and README](https://github.com/lyogavin/airllm)

The third-party OpenAI-compatible wrapper reports roughly six seconds per generated token for Qwen2.5-0.5B-Instruct in its four-core x86 CPU container and roughly three minutes for the first request including download and splitting. At that measured rate, a 64-token response takes roughly six minutes of decoding. The wrapper queues requests behind a single generation slot and currently lacks tool-call parsing. The numbers describe that specific environment. ReidX's Ollama host was not benchmarked. [Wrapper measurements](https://github.com/mkamranr/airllm-openai-server/blob/main/docs/running.md) · [Wrapper request support](https://github.com/mkamranr/airllm-openai-server/blob/main/docs/usage.md)

For an optimized CPU baseline, llama.cpp supports quantized weights and includes a benchmark that distinguishes prompt processing from token generation. Start from the already configured small model and record its actual quantization, effective context, concurrency, CPU and RAM. In Ollama, a lower context reduces memory demands, and increased parallelism raises them. Test one active generation before increasing parallelism or adding more resident models. Preserve the embeddings service while measuring chat load. [llama.cpp](https://github.com/ggml-org/llama.cpp) · [llama-bench](https://github.com/ggml-org/llama.cpp/tree/master/tools/llama-bench) · [Ollama concurrency and memory](https://docs.ollama.com/faq)

## Acceptance criteria for a pilot

1. Use benign summarization or classification samples. Compare the same model family and parameter count where both formats exist. Record quantization differences and keep input and output limits fixed.
2. Measure cold-start time including shard preparation, warm time to first token, decode rate, p50 and p95 request latency, peak RSS, swap activity, disk read volume and shard footprint. Repeat at one and two concurrent requests. Include a simultaneous embedding request and record whether its latency degrades.
3. Score task outputs against the same reference answers. Record errors, cancellations and timeouts separately from successful latency. Use the current CPU baseline as the comparison.
4. If a workload meets its latency, quality and resource budgets, run the wrapper separately with an isolated cache and a bounded queue. Put the experimental route behind one opt-in LiteLLM alias and restrict it to text-only work. Leave the existing aliases as the fallback during evaluation. Require streaming and cancellation checks before exposing it to interactive use.

See the [ReidX README](../README.md) for setup and profile configuration.
