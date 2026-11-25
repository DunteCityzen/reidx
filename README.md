# ReidX 1.0

<img width="1234" height="953" alt="image" src="https://github.com/user-attachments/assets/45031fc7-1ad1-46df-914b-8b021485d69e" />

ReidX is a terminal workspace for coding, research and technical writing, created by Mr. Robot.TxT. Use one model for a small job, or let a lead agent hand research, edits, tests and review to different specialists. LiteLLM keeps the model choices in one place. ReidX keeps conversations, memory and workflow files on your machine.

## Install and start

The 1.0 release contains a compiled Linux x64 terminal and workspace server, a setup script, and editable agent, command, skill and memory files. The setup script and memory MCP use Python 3.11+ with `venv` and `pip`. You also need a LiteLLM gateway and an Ollama server for the Nomic embedding model. Ollama can run on the same machine or on a separate host.

Download the compiled archive and its checksum from the repository’s Releases page, then run these commands from the download directory.

```sh
sha256sum -c reidx-1.0.0-linux-x64.tar.gz.sha256
tar -xzf reidx-1.0.0-linux-x64.tar.gz
cd reidx-1.0.0-linux-x64
python3 harness/install-reidx.py
export REIDX_HOME="$HOME/.local/share/reidx"
export PATH="$REIDX_HOME/bin:$PATH"
reidx --version
```

Open `$REIDX_HOME/config/litellm/config.yaml`. Set the `nomic-embed` entry's `api_base` to the Ollama address as seen from the gateway. The setup command also needs to reach that address. Then run `reidx setup`. It offers to install missing local Ollama on Linux, asks before pulling the configured model, and checks that it can produce a vector. The Ollama host must already be running when it is remote.

If you already run LiteLLM, merge the shipped role aliases into your gateway config or point `reidx setup --litellm-config /path/to/config.yaml` at your existing file. For a fresh gateway, install LiteLLM Proxy in a separate environment on the gateway host. The example uses OpenRouter for chat. Use `config/litellm/env.example` in the installation as a template for your gateway credentials. Store the filled-in copy outside the repository with permissions set to `600`. Load `OPENROUTER_API_KEY` and `LITELLM_MASTER_KEY` in the gateway service's environment, then start it. [LiteLLM configuration](https://docs.litellm.ai/docs/proxy/configuration/overview)

```sh
python3 -m venv "$HOME/.local/share/reidx-gateway"
"$HOME/.local/share/reidx-gateway/bin/pip" install 'litellm[proxy]'
"$HOME/.local/share/reidx-gateway/bin/litellm" \
  --host 127.0.0.1 --port 4000 --config "$REIDX_HOME/config/litellm/config.yaml"
```

In the terminal where you use ReidX, set `LITELLM_MASTER_KEY` to your LiteLLM client credential. If the gateway is elsewhere, set `REIDX_SAFE_LLM_URL` to its API base ending in `/v1`. The safe URL also serves memory lookups, including in burst mode.

```sh
reidx setup --gateway-url "${REIDX_SAFE_LLM_URL:-http://127.0.0.1:4000/v1}"
cd /path/to/your/project
reidx launch
```

## Launch modes and arguments

<img width="1248" height="993" alt="image" src="https://github.com/user-attachments/assets/bb89583a-cf8c-4736-89b3-0dc27de2f1e6" />

Run `reidx` or `reidx launch` for the normal interactive session. Run `reidx launch --mode burst` to use the burst gateway. Launcher options come before `--`, and arguments for the compiled CLI come after it.

| Task | Command |
| --- | --- |
| Open a project | `reidx launch -- /path/to/project` |
| Start with a prompt | `reidx launch -- --prompt "Summarize this repository."` |
| Resume the latest session | `reidx launch --continue` |
| Resume a specific session in burst | `reidx launch --mode burst --session ses_YOUR_ID` |
| Use the minimal interface | `reidx launch -- mini` |
| List model aliases | `reidx launch -- models` |
| List sessions in this workspace | `reidx launch -- session list` |

Use `run` for a one-shot prompt or a script.

```sh
reidx launch -- run "Summarize this repository."
reidx launch --mode burst -- run --agent research --model litellm/researcher "Summarize the design."
reidx launch -- run --file README.md --format json "List the prerequisites."
reidx launch -- run --session ses_YOUR_ID "Summarize what we decided."
```

Run `reidx launch --help` for launcher options, `reidx launch -- --help` for compiled CLI commands, and `reidx launch -- run --help` or `reidx launch -- mini --help` for subcommand options. Use `reidx setup --help` for prerequisite checks.

## Working with agents

<img width="1242" height="932" alt="image" src="https://github.com/user-attachments/assets/2ae05fd0-a1c4-43e7-8e8a-3995f10d647f" />


Use **Build** for a task that needs coordination, **Plan** to work out an approach, and **Single-model** when you want one selected alias throughout. The terminal's agent selector lets you switch leads.

| Agent | Work it owns | LiteLLM alias |
| --- | --- | --- |
| Build | Coordinates work and hands off bounded tasks | `orchestrator` |
| Architect | Breaks down a change and defines acceptance criteria | `planner` |
| Researcher | Gathers evidence and checks sources | `researcher` |
| Implementer | Owns edits to a shared set of files | `implementer` |
| Code reviewer | Reviews changes independently | `code-reviewer` |
| Test engineer | Runs focused checks and reports results | `test-engineer` |
| Evaluator | Checks the delivered result against the original task | `evaluator` |
| Security and vision analysts | Review code or configuration for security issues, or interpret images | `security-analyst`, `vision-analyst` |
| Writer and memory curator | Draft material or capture reusable lessons | `writer`, `memory-curator` |

Start with `/task` for a substantial request, `/implement` for a code change, or `/multi-review` for independent specialist reviews. `/single-model` uses the current model alias for its worker and reviewer. `/model-panel` explicitly requests five separately routed opinions. For writing, use `/write-report` or `/blog-post`. The commands and their supporting skills are ordinary Markdown files.

Exit the terminal normally and use the printed resume command to return to that conversation. From the same workspace and installation, `reidx launch --continue` opens the latest session. You can also use `reidx launch --session ses_…` with a specific session ID. Add `--mode burst` when resuming in burst.

## Change a model in one place

The shipped terminal exposes only the LiteLLM provider. Each agent refers to an alias such as `litellm/implementer`. LiteLLM resolves it using `model_name: implementer`. To change who handles implementation, keep the alias and change the provider model and credentials under `litellm_params`.

```yaml
- model_name: implementer
  litellm_params:
    model: openai/gpt-4.1
    api_key: os.environ/OPENAI_API_KEY
```

Replace the whole deployment's provider-specific settings when switching providers, then restart the gateway. Choose models with the tool or image capabilities required by their roles and check that the context and output limits in `reidx/reidx.json` match the deployment. The bundled OpenRouter entries are starting mappings. Confirm availability and limits with your provider.

Safe mode uses the per-deployment parallel limits in the sample YAML. To run a separate burst gateway, generate a second YAML and start LiteLLM with it on port 4001. Provider quotas and retry settings still apply. After changing a model in safe mode, regenerate the burst file if you use both.

```sh
"$REIDX_HOME/.venv/bin/python" "$REIDX_HOME/scripts/generate-burst-config.py" \
  "$REIDX_HOME/config/litellm/config.yaml" "$REIDX_HOME/config/litellm/config-burst.yaml"
reidx launch --mode burst
```

Use `REIDX_BURST_LLM_URL` for a burst gateway on another host. Keep the two profiles' role aliases consistent. Reserve `nomic-embed` for embeddings. If you change its underlying model, close running ReidX sessions, move the old `memory/memory.sqlite3` aside, then reopen ReidX and run `/reindex-memory` to rebuild vectors from the text files.

## Memory and local files

Run `/recall` to bring a relevant lesson into a session, or `/learn` after a task to record what worked. When a method is repeatable, ReidX can propose a draft under `learning/skill-inbox/`. Review it and copy its skill directory to `reidx/skills/` to activate it. Run `/reindex-memory` after editing the text files you want searchable.

Inside `$REIDX_HOME`, `reidx/` holds active configuration, agents, commands and skills. `memory/` holds Markdown and its local SQLite index. `runtime/` holds conversation data and local caches. To move from an earlier ReidX installation, exit all sessions and install into a new prefix with `--migrate-from /path/to/old/reidx`. This copies conversations, memory and skill drafts. Merge custom settings and files into the new `reidx/` directory by hand. Workspace configuration now uses `reidx.json` or `.reidx/reidx.json`.

## License

ReidX changes are licensed under [MIT](LICENSE). The [upstream MIT notice](UPSTREAM-LICENSE) is included in the release. See the [local inference notes](docs/AIRLLM.md) for the AirLLM evaluation.
