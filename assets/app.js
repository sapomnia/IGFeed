(async function () {
  const grid = document.getElementById("grid");
  const updatedEl = document.getElementById("updated");

  function el(tag, props = {}, children = []) {
    const n = document.createElement(tag);
    Object.assign(n, props);
    for (const c of [].concat(children)) {
      if (c == null) continue;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return n;
  }

  function formatUpdated(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return "Ultimo aggiornamento: " +
        d.toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" });
    } catch { return ""; }
  }

  function render(items) {
    grid.innerHTML = "";
    if (!items || !items.length) {
      grid.appendChild(el("p", { className: "empty", textContent: "Nessun post disponibile." }));
      return;
    }
    const frag = document.createDocumentFragment();
    for (const item of items) {
      const a = el("a", {
        className: "card",
        href: item.url,
        target: "_blank",
        rel: "noopener noreferrer",
        title: item.caption || "Apri articolo",
      });
      const img = el("img", {
        src: item.image,
        alt: item.caption ? item.caption.slice(0, 120) : "Post Instagram",
        loading: "lazy",
        decoding: "async",
      });
      const overlay = el("div", { className: "overlay" },
        el("span", { textContent: item.caption || "" })
      );
      a.appendChild(img);
      a.appendChild(overlay);
      frag.appendChild(a);
    }
    grid.appendChild(frag);
  }

  try {
    const res = await fetch("feed.json", { cache: "no-cache" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    render(data.items || []);
    updatedEl.textContent = formatUpdated(data.updated_at);
  } catch (err) {
    console.error(err);
    grid.innerHTML = "";
    grid.appendChild(el("p", { className: "error", textContent: "Impossibile caricare il feed." }));
  }
})();
