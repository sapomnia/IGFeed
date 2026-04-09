# Instagram → GitHub Pages

Griglia statica ospitata su GitHub Pages che mostra gli ultimi post Instagram.
Ogni immagine è cliccabile e porta all'articolo esterno indicato nella caption
dopo il marcatore **🔗**.

Un workflow GitHub Actions chiama la Instagram Graph API ogni 6 ore, scarica le
immagini nel repo e rigenera `feed.json`. Un secondo workflow rinnova in automatico
il long-lived token (60 giorni) una volta a settimana.

---

## 1. Requisiti lato Meta

1. Vai su <https://developers.facebook.com/apps>, crea un'app di tipo **Business**.
2. Aggiungi il prodotto **Instagram Graph API** (o "Instagram API with Instagram Login").
3. Collega l'account Instagram (deve essere Business o Creator).
4. Genera un **User Token** con il permesso `instagram_basic`.
5. Convertilo in **long-lived token** (dura ~60 giorni).

### Come convertire in long-lived token

Dall'Instagram API with Instagram Login:

```bash
curl -s -G "https://graph.instagram.com/access_token" \
  --data-urlencode "grant_type=ig_exchange_token" \
  --data-urlencode "client_secret=APP_SECRET" \
  --data-urlencode "access_token=SHORT_LIVED_TOKEN"
```

Copia `access_token` dalla risposta: è quello che metterai come secret.

---

## 2. Secret GitHub da impostare

Su **Settings → Secrets and variables → Actions → New repository secret**:

| Nome              | Valore                                                                       |
| ----------------- | ---------------------------------------------------------------------------- |
| `INSTAGRAM_TOKEN` | Il long-lived token ottenuto sopra                                           |
| `GH_PAT`          | Personal Access Token (classic) con scope `repo` — serve a `refresh_token.py` per riscrivere `INSTAGRAM_TOKEN` automaticamente |

Per il PAT: <https://github.com/settings/tokens> → *Generate new token (classic)*
→ scope `repo` → nessuna scadenza (o almeno 1 anno).

---

## 3. Abilitare GitHub Pages

**Settings → Pages → Source: Deploy from a branch → `main` / `(root)`**.

L'URL pubblico sarà `https://<utente>.github.io/<repo>/`.

---

## 4. Come scrivere le caption

In fondo alla caption del post Instagram metti il marcatore 🔗 seguito dal link,
per esempio:

```
Il mio ultimo articolo sul cambiamento climatico.

🔗 https://esempio.it/articolo
```

I post che **non** contengono il marcatore 🔗 vengono ignorati dalla griglia.

---

## 5. Struttura del progetto

```
.
├── .github/workflows/
│   ├── update-feed.yml      # ogni 6h: fetch + commit feed.json + immagini
│   └── refresh-token.yml    # settimanale: rinnova INSTAGRAM_TOKEN
├── scripts/
│   ├── fetch_instagram.py   # chiama Graph API e genera feed.json
│   └── refresh_token.py     # rinnova token e aggiorna secret GitHub
├── assets/
│   ├── style.css
│   └── app.js
├── images/                  # immagini scaricate (committate)
├── feed.json                # generato dall'Action
├── index.html               # pagina pubblica
└── requirements.txt
```

---

## 6. Test in locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export INSTAGRAM_TOKEN="..."
python scripts/fetch_instagram.py
```

Poi apri `index.html` con un piccolo web server (non `file://`):

```bash
python -m http.server 8000
# http://localhost:8000
```

---

## 7. Troubleshooting

- **"Nessun 🔗 nella caption"** → il post non ha il marcatore, verrà saltato.
- **Token scaduto** → lancia manualmente il workflow *Refresh Instagram token*
  (Actions → Run workflow) oppure rigenera il token a mano e aggiorna il secret.
- **Immagini non aggiornate** → forza `Run workflow` su *Update Instagram feed*.
- **La griglia mostra "Impossibile caricare il feed"** → stai aprendo `index.html`
  con `file://`. Serve un server HTTP (GitHub Pages, o `python -m http.server`).
