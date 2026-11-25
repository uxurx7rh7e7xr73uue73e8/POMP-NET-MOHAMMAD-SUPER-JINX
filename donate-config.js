/* ===================================================================
   POMP NET MOHAMMAD · Donation page config  (the ONLY place addresses live)
   - Each address is checked with its network's real checksum before it
     is shown (EIP-55 / Bech32 / Base58Check / TON CRC16).
   - A wrong or mistyped address is hidden automatically, never shown.
   - kind: evm | btc | tron | ton      color: #RRGGBB
   =================================================================== */
var JINX_DONATE = {
  brand: "POMP NET MOHAMMAD",
  edition: "SUPER JINX",
  bankCard: "6280231311605819",
  bankIntro: "",
  supportTelegram: "https://t.me/NovaTunneli",
  channel: "https://t.me/pompnet",
  intro: "قدرت ساخت، آزادی انتخاب، کنترل در دستان تو؛ اگر این مسیر برایت مفید بوده، همراهی تو به ادامه‌ی توسعه‌ی POMP NET جان می‌دهد.",
  intro_en: "If this project has been useful to you, you can help its development and improvement continue with a donation.",
  coins: []
};


/* POMP NET MOHAMMAD — SUPER JINX support-page visual identity.
   The existing owner-provided payment value stays in its single config field. */
(function () {
  var root = document.documentElement;
  root.setAttribute("data-theme", "dark");
  root.style.setProperty("--bg", "#050509");
  root.style.setProperty("--s1", "#100e1a");
  root.style.setProperty("--s2", "#171326");
  root.style.setProperty("--s3", "#1d1730");
  root.style.setProperty("--line", "rgba(139,53,255,.18)");
  root.style.setProperty("--line2", "rgba(139,53,255,.34)");
  root.style.setProperty("--tx", "#f4f0ff");
  root.style.setProperty("--tx2", "#c1b7d8");
  root.style.setProperty("--tx3", "#9589ad");
  root.style.setProperty("--gold", "#a96bff");
  root.style.setProperty("--gold2", "#c29aff");
  root.style.setProperty("--cr", "139,53,255");
  var css = [
    "body{background:#050509!important;color:#f4f0ff!important}",
    "body:before{background:radial-gradient(900px 440px at 70% -8%,rgba(139,53,255,.18),transparent 70%),radial-gradient(700px 420px at 0% 100%,rgba(22,140,255,.08),transparent 70%)!important}",
    ".top{border-color:rgba(139,53,255,.25)!important}",
    ".mark{border:1px solid rgba(139,53,255,.7)!important;color:#fff!important;background:linear-gradient(145deg,rgba(139,53,255,.32),rgba(22,140,255,.12))!important;box-shadow:0 0 24px rgba(139,53,255,.22)!important}",
    ".mark:after{content:'PJ';font:900 12px/1 var(--mono);letter-spacing:.08em}",
    ".brand b{color:#fff!important;font-weight:900!important}",
    ".brand small{color:#b98aff!important;font-weight:800!important;letter-spacing:.12em!important}",
    ".eyebrow,.intro h1 span,.kv dd.mono,.vw h3 .ico,.proc .n{color:#b98aff!important}",
    ".list,.detail,.proc{background:linear-gradient(145deg,#100e1a,#080711)!important;border-color:rgba(139,53,255,.28)!important;box-shadow:0 16px 42px rgba(0,0,0,.38),0 0 26px rgba(139,53,255,.07)!important}",
    ".btn-p{background:linear-gradient(110deg,#8b35ff,#5420a6)!important;color:#fff!important;box-shadow:0 8px 26px rgba(139,53,255,.25)!important}",
    ".btn-g:hover,.row:hover,.row[aria-checked=true]{background:rgba(139,53,255,.12)!important}",
    ".addr{border-color:rgba(139,53,255,.42)!important;background:#080711!important}",
    ".addr:hover,.vf input:focus{border-color:#8b35ff!important}",
    ".status i{background:#a96bff!important;box-shadow:0 0 0 3px rgba(139,53,255,.18)!important}",
    ".fab,.bot{background:#100e1a!important;border-color:rgba(139,53,255,.35)!important}",
    ".fab .ico,.fab:hover .ico{color:#b98aff!important}",
    ".foot{border-color:rgba(139,53,255,.22)!important}",
    ".foot a:hover{color:#b98aff!important}",
    ".kv,.facts,.proc div+div{border-color:rgba(139,53,255,.22)!important}",
    ".btn-p,.btn-g,.ib{border-radius:12px!important}"
  ].join("");
  function inject() {
    if (document.getElementById("pompnet-super-jinx-support-theme")) return;
    var style = document.createElement("style");
    style.id = "pompnet-super-jinx-support-theme";
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  }
  inject();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", inject, {once:true});
})();
