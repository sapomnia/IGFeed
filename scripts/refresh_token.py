#!/usr/bin/env python3
"""
Rinnova il long-lived Instagram token (validi ~60 giorni) chiamando
l'endpoint refresh_access_token di graph.instagram.com e aggiorna il
secret INSTAGRAM_TOKEN del repo GitHub tramite API.

Variabili d'ambiente richieste:
  INSTAGRAM_TOKEN   token long-lived attuale
  GH_PAT            Personal Access Token con scope `repo` (per scrivere il secret)
  GITHUB_REPOSITORY "owner/repo" (impostato automaticamente in Actions)

Opzionali:
  IG_SECRET_NAME    nome del secret da aggiornare (default INSTAGRAM_TOKEN)
"""

from __future__ import annotations

import base64
import os
import sys

import requests
from nacl import encoding, public


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def log(msg: str) -> None:
    print(msg, flush=True)


def refresh_ig_token(current: str) -> str:
    url = "https://graph.instagram.com/refresh_access_token"
    params = {"grant_type": "ig_refresh_token", "access_token": current}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        die(f"Refresh fallito ({r.status_code}): {r.text}")
    data = r.json()
    new_token = data.get("access_token")
    expires_in = data.get("expires_in")
    if not new_token:
        die(f"Risposta senza access_token: {data}")
    log(f"Nuovo token ottenuto, scade tra {expires_in} secondi "
        f"(~{int(expires_in) // 86400} giorni)")
    return new_token


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


def update_repo_secret(repo: str, pat: str, name: str, value: str) -> None:
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # 1. recupera public key del repo
    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers, timeout=30,
    )
    if r.status_code != 200:
        die(f"Get public-key fallito ({r.status_code}): {r.text}")
    pk_data = r.json()

    # 2. cifra il valore
    encrypted = encrypt_secret(pk_data["key"], value)

    # 3. PUT del secret
    r = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": pk_data["key_id"]},
        timeout=30,
    )
    if r.status_code not in (201, 204):
        die(f"Update secret fallito ({r.status_code}): {r.text}")
    log(f"Secret {name} aggiornato su {repo}")


def main() -> int:
    current = os.environ.get("INSTAGRAM_TOKEN") or die("INSTAGRAM_TOKEN mancante")
    pat = os.environ.get("GH_PAT") or die("GH_PAT mancante")
    repo = os.environ.get("GITHUB_REPOSITORY") or die("GITHUB_REPOSITORY mancante")
    name = os.environ.get("IG_SECRET_NAME", "INSTAGRAM_TOKEN")

    new_token = refresh_ig_token(current)
    update_repo_secret(repo, pat, name, new_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
