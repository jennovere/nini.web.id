/* NINI Customer Support — chat widget (modul terpisah, tidak mengubah halaman lain)
 * Cara pakai: tambahkan 1 baris sebelum </body> di halaman yang diinginkan:
 *   <script src="/assets/nini-chat.js" defer></script>      (halaman di root)
 *   <script src="../assets/nini-chat.js" defer></script>    (halaman di subfolder)
 * Endpoint: window.NINI_CHAT_ENDPOINT (default https://nini.web.id/api/chat)
 * Tidak menampilkan/menyimpan API key apa pun di sisi browser.
 */
(function () {
  "use strict";
  try {
    var ENDPOINT = window.NINI_CHAT_ENDPOINT || "https://nini.web.id/api/chat";
    var CS_URL = "https://wa.me/6285979513702";
    var REF_URL = "https://www.binance.com/register?ref=SR08WSSY";
    var WELCOME =
      "Halo 👋 Saya NINI Assistant.\n\n" +
      "Saya bisa membantu kamu mengenai:\n" +
      "• Daftar Binance (link referral resmi)\n" +
      "• Instalasi NINI Follower\n" +
      "• Setting NINI\n" +
      "• Koneksi Binance\n" +
      "• Copy trade\n" +
      "• Troubleshooting\n" +
      "• Penggunaan aplikasi\n\n" +
      "Ada yang ingin kamu tanyakan?";
    var QUICK = [
      "Cara daftar Binance",
      "Cara install NINI",
      "Cara setting Binance",
      "NINI tidak entry",
      "Cara setting copy trade",
      "NINI error",
    ];
    var ERR_TEXT =
      "Maaf, terjadi gangguan sementara. Coba lagi beberapa saat lagi ya, " +
      "atau hubungi CS NINI melalui tombol di bawah.";
    var TIMEOUT_MS = 30000;
    var MAX_INPUT = 1200;

    var history = [];
    var sending = false;

    // ---------- Styles ----------
    var css = [
      "#niniChatLauncher{position:fixed;width:56px;height:56px;border-radius:50%;",
      "background:#00c853;color:#081410;border:none;cursor:pointer;z-index:9998;",
      "box-shadow:0 10px 30px rgba(0,230,118,.45);display:flex;align-items:center;",
      "justify-content:center;transition:transform .15s ease}",
      "#niniChatLauncher:hover{transform:scale(1.06)}",
      "#niniChatPanel{position:fixed;z-index:9999;right:20px;width:min(380px,calc(100vw - 24px));",
      "height:min(560px,calc(100vh - 130px));background:#0a1f18;border:1px solid #12362a;",
      "border-radius:18px;box-shadow:0 30px 80px rgba(0,0,0,.55);display:none;",
      "flex-direction:column;overflow:hidden;font-family:Inter,system-ui,sans-serif}",
      "#niniChatPanel.open{display:flex}",
      ".niniC-head{display:flex;align-items:center;gap:10px;padding:12px 12px 12px 14px;",
      "background:linear-gradient(90deg,#0d2a20,#0a1f18);border-bottom:1px solid #12362a}",
      ".niniC-av{width:34px;height:34px;border-radius:50%;background:#12362a;border:1px solid",
      " rgba(255,215,0,.45);display:flex;align-items:center;justify-content:center;font-size:16px;",
      "object-fit:cover;flex:none}",
      ".niniC-ttl{flex:1;min-width:0}",
      ".niniC-ttl b{display:block;color:#fff;font-size:13.5px;font-weight:700;line-height:1.2}",
      ".niniC-ttl span{display:block;color:#7d8aa5;font-size:11px;margin-top:2px}",
      ".niniC-btn{width:30px;height:30px;border-radius:8px;border:1px solid #12362a;",
      "background:#0d2a20;color:#a0aec0;cursor:pointer;font-size:15px;line-height:1}",
      ".niniC-btn:hover{border-color:#00c853;color:#00e676}",
      ".niniC-body{flex:1;overflow-y:auto;padding:14px 12px;background:#081410;",
      "display:flex;flex-direction:column;gap:10px}",
      ".niniC-msg{max-width:86%;padding:10px 12px;border-radius:14px;font-size:13.5px;",
      "line-height:1.55;white-space:pre-wrap;word-break:break-word}",
      ".niniC-msg a{color:#00e676;text-decoration:underline;word-break:break-all}",
      ".niniC-msg a:hover{color:#69f0ae}",
      ".niniC-me a{color:#062b16}",
      ".niniC-bot{background:#0d2a20;border:1px solid #12362a;color:#e8eef7;",
      "align-self:flex-start;border-top-left-radius:4px}",
      ".niniC-me{background:#00c853;color:#062b16;align-self:flex-end;",
      "border-top-right-radius:4px;font-weight:500}",
      ".niniC-warn{background:#2a1503;border:1px solid #7c2d12;color:#fbbf24;",
      "align-self:flex-start;font-size:12.5px}",
      ".niniC-note{align-self:center;background:#12362a;color:#a0aec0;font-size:11.5px;",
      "padding:6px 10px;border-radius:999px;text-align:center}",
      ".niniC-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px;background:#081410}",
      ".niniC-chip{border:1px solid rgba(255,215,0,.45);color:#ffd700;background:rgba(255,215,0,.06);",
      "border-radius:999px;padding:6px 10px;font-size:11.5px;cursor:pointer;font-family:inherit}",
      ".niniC-chip:hover{background:rgba(255,215,0,.16)}",
      ".niniC-typing{display:none;gap:4px;align-items:center;align-self:flex-start;",
      "background:#0d2a20;border:1px solid #12362a;padding:11px 13px;border-radius:14px}",
      ".niniC-typing i{width:6px;height:6px;border-radius:50%;background:#00e676;",
      "display:inline-block;animation:niniCblink 1.2s infinite}",
      ".niniC-typing i:nth-child(2){animation-delay:.2s}",
      ".niniC-typing i:nth-child(3){animation-delay:.4s}",
      "@keyframes niniCblink{0%,80%,100%{opacity:.25}40%{opacity:1}}",
      ".niniC-foot{border-top:1px solid #12362a;background:#0a1f18;padding:8px 10px}",
      ".niniC-row{display:flex;gap:8px;align-items:flex-end}",
      ".niniC-input{flex:1;min-height:38px;max-height:96px;resize:none;background:#081410;",
      "border:1px solid #12362a;border-radius:12px;color:#e8eef7;padding:10px 12px;",
      "font-size:13.5px;font-family:inherit;outline:none}",
      ".niniC-input:focus{border-color:#00c853}",
      ".niniC-send{width:40px;height:40px;flex:none;border:none;border-radius:12px;",
      "background:#00c853;color:#062b16;cursor:pointer;display:flex;align-items:center;",
      "justify-content:center}",
      ".niniC-send:disabled{opacity:.5;cursor:not-allowed}",
      ".niniC-sub{display:flex;justify-content:space-between;gap:8px;margin-top:6px;",
      "font-size:10.5px;color:#7d8aa5}",
      ".niniC-sub a{color:#00e676;text-decoration:none}",
      ".niniC-sub a:hover{text-decoration:underline}",
      ".niniC-promo{position:relative;align-self:stretch;background:linear-gradient(135deg,#12261d,#0a1f18);",
      "border:1px solid rgba(255,215,0,.5);border-radius:14px;padding:13px 13px 14px;",
      "box-shadow:0 12px 30px -18px rgba(255,215,0,.6)}",
      ".niniC-promoBadge{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.09em;",
      "color:#ffd700;border:1px solid rgba(255,215,0,.5);background:rgba(255,215,0,.08);",
      "border-radius:999px;padding:3px 9px;text-transform:uppercase}",
      ".niniC-promo h4{margin:9px 0 4px;color:#fff;font-size:14.5px;font-weight:700;line-height:1.3}",
      ".niniC-promo p{margin:0;color:#a9b6cc;font-size:12.5px;line-height:1.55;white-space:pre-wrap}",
      ".niniC-promoCta{margin-top:11px;display:flex;gap:7px;align-items:stretch}",
      ".niniC-promoBtn{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:6px;",
      "background:#ffd700;color:#081410;border:none;border-radius:10px;padding:9px 10px;",
      "font-size:13px;font-weight:700;text-decoration:none;font-family:inherit;cursor:pointer}",
      ".niniC-promoBtn:hover{background:#ffe14d}",
      ".niniC-promoLater{background:none;border:1px solid #12362a;color:#7d8aa5;border-radius:10px;",
      "padding:9px 11px;font-size:12px;cursor:pointer;font-family:inherit;flex:none}",
      ".niniC-promoLater:hover{color:#a0aec0;border-color:#00c853}",
      ".niniC-promoX{position:absolute;top:7px;right:7px;width:22px;height:22px;border-radius:6px;",
      "border:none;background:transparent;color:#7d8aa5;cursor:pointer;font-size:14px;line-height:1}",
      ".niniC-promoX:hover{color:#ffd700}",
      "@media (max-width:480px){#niniChatPanel{height:min(70vh,calc(100vh - 120px));",
      "width:calc(100vw - 16px);right:8px}",
    ].join("");

    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);

    // ---------- Posisi launcher (hindari tombol WhatsApp melayang) ----------
    function hasFixedWhatsApp() {
      var links = document.querySelectorAll('a[href*="wa.me"]');
      for (var i = 0; i < links.length; i++) {
        try {
          if (getComputedStyle(links[i]).position === "fixed") return true;
        } catch (e) {}
      }
      return false;
    }
    var bottomPx = hasFixedWhatsApp() ? 92 : 24;
    var rightPx = 20;

    // ---------- Launcher ----------
    var launcher = document.createElement("button");
    launcher.id = "niniChatLauncher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", "Buka chat NINI Customer Support");
    launcher.style.bottom = bottomPx + "px";
    launcher.style.right = rightPx + "px";
    launcher.innerHTML =
      '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';

    // ---------- Panel ----------
    var panel = document.createElement("div");
    panel.id = "niniChatPanel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "NINI Customer Support");
    panel.style.bottom = bottomPx + 66 + "px";

    function el(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text !== undefined) n.textContent = text;
      return n;
    }

    // Teks pesan → URL otomatis jadi <a> sekali klik (tanpa innerHTML, aman XSS)
    var URL_RE = /https?:\/\/[^\s<>"']+/gi;
    function linkify(node, text) {
      var s = text === undefined || text === null ? "" : String(text);
      var last = 0;
      var m;
      URL_RE.lastIndex = 0;
      while ((m = URL_RE.exec(s))) {
        var url = m[0].replace(/[.,;:!?)\]}'"]+$/, "");
        if (url.length < 12) continue;
        if (m.index > last) node.appendChild(document.createTextNode(s.slice(last, m.index)));
        var a = document.createElement("a");
        a.className = "niniC-link";
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = url;
        node.appendChild(a);
        last = m.index + url.length;
        URL_RE.lastIndex = last;
      }
      if (last < s.length) node.appendChild(document.createTextNode(s.slice(last)));
      return node;
    }

    // header
    var head = el("div", "niniC-head");
    var av = document.createElement("img");
    av.className = "niniC-av";
    av.alt = "";
    av.src = "/assets/nini_logo.png";
    av.onerror = function () {
      av.remove();
      var s = el("span", "niniC-av", "👑");
      head.insertBefore(s, head.firstChild);
    };
    head.appendChild(av);
    var ttl = el("div", "niniC-ttl");
    ttl.appendChild(el("b", null, "NINI Customer Support"));
    ttl.appendChild(el("span", null, "NINI Assistant • Balas cepat"));
    head.appendChild(ttl);
    var btnMin = el("button", "niniC-btn", "–");
    btnMin.type = "button";
    btnMin.title = "Minimize";
    btnMin.setAttribute("aria-label", "Minimalkan chat");
    var btnClose = el("button", "niniC-btn", "×");
    btnClose.type = "button";
    btnClose.title = "Close";
    btnClose.setAttribute("aria-label", "Tutup chat");
    head.appendChild(btnMin);
    head.appendChild(btnClose);

    // body
    var body = el("div", "niniC-body");
    body.setAttribute("role", "log");
    var msgWelcome = el("div", "niniC-msg niniC-bot", WELCOME);
    body.appendChild(msgWelcome);
    var typing = el("div", "niniC-typing");
    typing.appendChild(el("i"));
    typing.appendChild(el("i"));
    typing.appendChild(el("i"));
    body.appendChild(typing);

    // chips
    var chips = el("div", "niniC-chips");
    QUICK.forEach(function (q) {
      var c = el("button", "niniC-chip", q);
      c.type = "button";
      c.addEventListener("click", function () {
        send(q);
      });
      chips.appendChild(c);
    });

    // footer
    var foot = el("div", "niniC-foot");
    var row = el("div", "niniC-row");
    var input = document.createElement("textarea");
    input.className = "niniC-input";
    input.rows = 1;
    input.maxLength = MAX_INPUT;
    input.placeholder = "Tulis pertanyaanmu… (Enter kirim, Shift+Enter baris baru)";
    input.setAttribute("aria-label", "Pesan untuk NINI Assistant");
    var sendBtn = document.createElement("button");
    sendBtn.className = "niniC-send";
    sendBtn.type = "button";
    sendBtn.setAttribute("aria-label", "Kirim pesan");
    sendBtn.innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>';
    row.appendChild(input);
    row.appendChild(sendBtn);
    var sub = el("div", "niniC-sub");
    var subLeft = el("span", null, "AI bisa salah — untuk hal penting, konfirmasi ke Admin.");
    var subRight = document.createElement("a");
    subRight.href = CS_URL;
    subRight.target = "_blank";
    subRight.rel = "noopener noreferrer";
    subRight.textContent = "Hubungi Admin →";
    sub.appendChild(subLeft);
    sub.appendChild(subRight);
    foot.appendChild(row);
    foot.appendChild(sub);

    panel.appendChild(head);
    panel.appendChild(body);
    panel.appendChild(chips);
    panel.appendChild(foot);
    document.body.appendChild(launcher);
    document.body.appendChild(panel);

    // ---------- perilaku ----------
    function scrollDown() {
      body.scrollTop = body.scrollHeight;
    }
    function addMsg(cls, text) {
      var m = el("div", "niniC-msg " + cls);
      linkify(m, text);
      body.insertBefore(m, typing);
      scrollDown();
      return m;
    }
    function addNote(text) {
      var m = el("div", "niniC-note");
      linkify(m, text);
      body.insertBefore(m, typing);
      scrollDown();
      return m;
    }

    // ---------- Promo popup: daftar Binance (link referral resmi NINI) ----------
    var promoNode = null;
    var promoTimer = null;
    function promoOff() {
      try {
        return sessionStorage.getItem("niniChatPromo") === "off";
      } catch (e) {
        return false;
      }
    }
    function dismissPromo() {
      if (promoTimer) {
        clearTimeout(promoTimer);
        promoTimer = null;
      }
      if (promoNode) {
        promoNode.remove();
        promoNode = null;
      }
      try {
        sessionStorage.setItem("niniChatPromo", "off");
      } catch (e) {}
    }
    function removePromoTemp() {
      if (promoTimer) {
        clearTimeout(promoTimer);
        promoTimer = null;
      }
      if (promoNode) {
        promoNode.remove();
        promoNode = null;
      }
    }
    function buildPromo() {
      if (promoNode) return promoNode;
      var n = el("div", "niniC-promo");
      var x = el("button", "niniC-promoX", "×");
      x.type = "button";
      x.title = "Tutup promo";
      x.setAttribute("aria-label", "Tutup promo daftar Binance");
      x.addEventListener("click", dismissPromo);
      var badge = el("span", "niniC-promoBadge", "🎁 Promo — Referral Resmi");
      var h = el("h4", null, "Belum punya akun Binance?");
      var p = el(
        "p",
        null,
        "Daftar lewat link referral resmi NINI, lalu dapatkan potongan fee trading, setup dibantu admin, dan dukungan penuh selamanya."
      );
      var cta = el("div", "niniC-promoCta");
      var btn = document.createElement("a");
      btn.className = "niniC-promoBtn";
      btn.href = REF_URL;
      btn.target = "_blank";
      btn.rel = "noopener noreferrer";
      btn.textContent = "Daftar Akun Binance →";
      var later = el("button", "niniC-promoLater", "Nanti");
      later.type = "button";
      later.addEventListener("click", dismissPromo);
      cta.appendChild(btn);
      cta.appendChild(later);
      n.appendChild(x);
      n.appendChild(badge);
      n.appendChild(h);
      n.appendChild(p);
      n.appendChild(cta);
      promoNode = n;
      return n;
    }
    function queuePromo() {
      if (promoOff() || promoTimer || promoNode) return;
      promoTimer = setTimeout(function () {
        promoTimer = null;
        if (promoOff()) return;
        body.insertBefore(buildPromo(), typing);
        scrollDown();
      }, 1000);
    }

    function openPanel() {
      panel.classList.add("open");
      launcher.setAttribute("aria-expanded", "true");
      scrollDown();
      queuePromo();
      setTimeout(function () {
        input.focus();
      }, 60);
    }
    function closePanel() {
      panel.classList.remove("open");
      launcher.setAttribute("aria-expanded", "false");
    }

    launcher.addEventListener("click", function () {
      if (panel.classList.contains("open")) closePanel();
      else openPanel();
    });
    btnMin.addEventListener("click", closePanel);
    btnClose.addEventListener("click", function () {
      closePanel();
      removePromoTemp();
      try {
        history = [];
        body.querySelectorAll(".niniC-msg:not(#x)").forEach(function (n) {
          if (n !== msgWelcome) n.remove();
        });
        chips.style.display = "";
      } catch (e) {}
    });

    function setSending(v) {
      sending = v;
      typing.style.display = v ? "flex" : "none";
      sendBtn.disabled = v;
      input.disabled = v;
      if (v) scrollDown();
    }

    function send(text) {
      var msg = (text !== undefined ? text : input.value).trim();
      if (!msg || sending) return;
      if (msg.length > MAX_INPUT) {
        addNote("Pesan terlalu panjang. Mohon ringkas dulu ya (maks. 1.200 karakter).");
        return;
      }
      if (text === undefined) input.value = "";
      addMsg("niniC-me", msg);
      chips.style.display = "none";
      setSending(true);

      var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
      var timer = ctrl ? setTimeout(function () {
        ctrl.abort();
      }, TIMEOUT_MS) : null;

      fetch(ENDPOINT, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: msg, history: history.slice(-12) }),
        signal: ctrl ? ctrl.signal : undefined,
      })
        .then(function (r) {
          return r.json().catch(function () {
            return {};
          });
        })
        .then(function (d) {
          history.push({ role: "user", text: msg });
          var reply =
            typeof d.reply === "string" && d.reply
              ? d.reply
              : ERR_TEXT;
          addMsg("niniC-bot", reply);
          history.push({ role: "assistant", text: reply });
          if (history.length > 24) history = history.slice(-24);
          if (d.credential) {
            addMsg(
              "niniC-warn",
              "⚠️ Peringatan: jangan pernah membagikan API Secret, password, OTP, " +
                "2FA, seed phrase, atau private key kepada siapa pun — termasuk tim NINI. " +
                "Segera buat ulang API key Anda di Binance bila sudah terlanjur dikirim."
            );
          }
          if (d.fallback) addNote("Mode gangguan: jawaban terbatas sementara.");
        })
        .catch(function () {
          addMsg("niniC-bot", ERR_TEXT);
        })
        .then(function () {
          if (timer) clearTimeout(timer);
          setSending(false);
          input.focus();
        });
    }

    sendBtn.addEventListener("click", function () {
      send();
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
  } catch (err) {
    // widget gagal muat -> diamkan, jangan merusak halaman
    if (window.console && console.warn) console.warn("NINI chat:", err);
  }
})();
