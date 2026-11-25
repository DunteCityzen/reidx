"""Interactive setup for ReidX's memory embedding prerequisite."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

import httpx
import yaml

class Denied(Exception):
    pass

EMBEDDING_ALIAS = "nomic-embed"
OLLAMA_INSTALLER = "https://ollama.com/install.sh"


def configure_parser(parser):
    parser.add_argument(
        "--litellm-config", type=Path,
        default=Path.home() / ".config/litellm/config.yaml",
        help="LiteLLM YAML containing the Ollama embedding alias",
    )
    parser.add_argument("--gateway-url", help="Also verify the alias through this LiteLLM API base URL")


def confirm(question):
    return input(f"{question} [y/N] ").strip().casefold() in {"y", "yes"}


def embedding_route(path):
    try:
        config = yaml.safe_load(path.expanduser().read_text())
        routes = [row["litellm_params"] for row in config["model_list"]
                  if row.get("model_name") == EMBEDDING_ALIAS]
        if len(routes) != 1:
            raise ValueError
        model = routes[0]["model"].removeprefix("ollama/")
        endpoint = routes[0]["api_base"].rstrip("/")
        url = urlsplit(endpoint)
        if (not routes[0]["model"].startswith("ollama/") or not model or
                model.startswith("-") or url.scheme not in {"http", "https"} or
                not url.hostname or url.username or url.password or url.path or
                url.query or url.fragment):
            raise ValueError
        return model, endpoint
    except (OSError, KeyError, TypeError, AttributeError, ValueError, yaml.YAMLError):
        raise Denied(f"Expected one explicit Ollama route for {EMBEDDING_ALIAS} in {path}.") from None


def request_json(url, payload=None, headers=None):
    response = httpx.request(
        "GET" if payload is None else "POST", url, json=payload, headers=headers,
        timeout=30, follow_redirects=False,
    )
    response.raise_for_status()
    return response.json()


def install_ollama():
    if not confirm("Download and run the official Linux Ollama installer? It may request sudo and start Ollama."):
        print("Setup stopped. Ollama is required for memory embeddings.")
        return None
    with tempfile.TemporaryDirectory(prefix="reidx-ollama-") as directory:
        script = Path(directory) / "install.sh"
        with urlopen(OLLAMA_INSTALLER, timeout=30) as response, script.open("wb") as file:
            shutil.copyfileobj(response, file)
        subprocess.run(["sh", str(script)], check=True)
    binary = shutil.which("ollama")
    if not binary:
        raise Denied("Ollama installation finished without an ollama executable on PATH.")
    return binary


def setup(args):
    model, endpoint = embedding_route(args.litellm_config)
    print(f"Memory alias {EMBEDDING_ALIAS} uses {model} at {endpoint}.")
    try:
        tags = request_json(endpoint + "/api/tags")
    except (httpx.ConnectError, httpx.ConnectTimeout):
        local = urlsplit(endpoint).hostname in {"localhost", "127.0.0.1", "::1"}
        if not local:
            raise Denied("The configured remote Ollama server is unreachable. Start it on its host and rerun setup.") from None
        if shutil.which("ollama"):
            raise Denied("Start the local Ollama service and rerun setup.") from None
        if install_ollama() is None:
            return 1
        tags = request_json(endpoint + "/api/tags")
    installed = {row.get("name") for row in tags["models"]}
    if model not in installed and f"{model}:latest" not in installed:
        if not confirm(f"Pull {model} onto the configured Ollama server?"):
            print("Setup stopped. The embedding model is required.")
            return 1
        binary = shutil.which("ollama")
        if not binary:
            raise Denied("Run setup on the Ollama host or install the Ollama CLI locally to run the approved pull.")
        subprocess.run([binary, "pull", model], check=True, env={**os.environ, "OLLAMA_HOST": endpoint})

    result = request_json(endpoint + "/api/embed", {
        "model": model, "input": "search_query: ReidX memory setup",
    })
    vector = (result.get("embeddings") or [[]])[0]
    if not vector:
        raise Denied("Ollama returned an empty embedding.")
    print(f"Ollama embedding verified ({len(vector)} dimensions).")

    if args.gateway_url:
        key = os.environ.get("LITELLM_MASTER_KEY")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        result = request_json(args.gateway_url.rstrip("/") + "/embeddings", {
            "model": EMBEDDING_ALIAS, "input": ["search_query: ReidX memory setup"],
        }, headers)
        gateway_vector = (result.get("data") or [{}])[0].get("embedding", [])
        if len(gateway_vector) != len(vector):
            raise Denied("LiteLLM returned an unexpected embedding dimension.")
        print(f"LiteLLM alias {EMBEDDING_ALIAS} verified.")
    return 0


def run(args):
    try:
        return setup(args)
    except KeyboardInterrupt:
        print("\nSetup interrupted. Rerun setup to check progress.")
        return 130
    except EOFError:
        print("\nSetup stopped before approval.")
        return 1
    except Denied as error:
        print(error)
    except httpx.HTTPStatusError as error:
        print(f"Setup request failed with HTTP {error.response.status_code}.")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, httpx.RequestError,
            subprocess.CalledProcessError):
        print("Setup failed. Check the Ollama and LiteLLM services, then retry.")
    return 2

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="reidx setup", description=__doc__)
    configure_parser(parser)
    raise SystemExit(run(parser.parse_args()))
