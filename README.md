# IGFeed — I pezzi data-driven di Riccardo Saporiti

Griglia statica ospitata su GitHub Pages che mostra gli ultimi post Instagram.
Ogni immagine è cliccabile e porta all'articolo esterno indicato nella caption
dopo il marcatore **🔗**.

Un workflow GitHub Actions chiama la Instagram Graph API **una volta al giorno
alle 19:00 ora italiana** (con gestione automatica del cambio solare/legale),
scarica le immagini nel repo e rigenera `feed.json`. Un secondo workflow rinnova
in automatico il long-lived token (60 giorni) una volta a settimana.

**URL pubblico**: <https://sapomnia.github.io/IGFeed/>

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

## 5. Quando si aggiorna

Il workflow *Update Instagram feed* gira **una volta al giorno alle 19:00 ora
italiana** (sia d'estate con CEST che d'inverno con CET). GitHub Actions
schedula in UTC e non conosce il DST, quindi il workflow ha due slot cron:

- `0 17 * * *` → 19:00 CEST (estate)
- `0 18 * * *` → 19:00 CET (inverno)

Uno step iniziale legge l'ora reale nel fuso `Europe/Rome` e fa proseguire il
job solo nello slot corretto; l'altro si auto-skippa in pochi secondi. Il
risultato è che nella cronologia di Actions vedrai **due run al giorno**, una
che lavora davvero e una "fantasma" che si ferma subito: è normale.

Il cambio ora legale ↔ solare (ultima domenica di marzo e di ottobre) è gestito
automaticamente dal sistema operativo del runner, non serve intervenire.

**Forzare un aggiornamento immediato**: Actions → *Update Instagram feed* →
*Run workflow*. I run manuali bypassano il gate orario e partono subito.

**Ritardi di GitHub**: le schedule possono slittare di 5–30 minuti nei momenti
di picco. Il gate tollera ritardi fino a 59 minuti; oltre, la run del giorno
salta e bisogna lanciarla a mano.

---

## 6. Struttura del progetto

```
.
├── .github/workflows/
│   ├── update-feed.yml      # 1x/giorno alle 19:00 Europe/Rome (DST-aware)
│   └── refresh-token.yml    # settimanale: rinnova INSTAGRAM_TOKEN
├── scripts/
│   ├── fetch_instagram.py   # chiama Graph API e genera feed.json
│   └── refresh_token.py     # rinnova token e aggiorna secret GitHub
├── assets/
│   ├── style.css            # palette #7284A8 / #070707, font Futura
│   └── app.js               # legge feed.json e renderizza la griglia
├── images/                  # immagini scaricate (committate)
├── feed.json                # generato dall'Action
├── index.html               # pagina pubblica
└── requirements.txt
```

---

## 7. Test in locale

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

## 8. Troubleshooting

- **"Nessun 🔗 nella caption"** → il post non ha il marcatore, verrà saltato.
- **Token scaduto** → lancia manualmente il workflow *Refresh Instagram token*
  (Actions → Run workflow) oppure rigenera il token a mano e aggiorna il secret.
- **Immagini non aggiornate** → forza `Run workflow` su *Update Instagram feed*.
- **Vedo due run al giorno di "Update Instagram feed", una vuota** → è il gate
  anti-DST, vedi sezione 5. Non è un errore.
- **La run del giorno è saltata** → GitHub Actions ha ritardato oltre 59 minuti.
  Lancia a mano *Run workflow*.
- **La griglia mostra "Impossibile caricare il feed"** → stai aprendo `index.html`
  con `file://`. Serve un server HTTP (GitHub Pages, o `python -m http.server`).
- **Il font non è Futura su Windows/Android** → Futura è proprietario. Su quei
  sistemi il CSS cade automaticamente su Century Gothic / Avenir / Trebuchet MS,
  che sono geometricamente simili.
