from pathlib import Path

p = Path("apps/web/src/pages/subscription.tsx")
s = p.read_text(encoding="utf-8")

replacements = [
    (
        'const protocolColor: Record<string, string> = {\n  vless: "#a3e635",\n  vmess: "#7dd3fc",\n  trojan: "#fbbf24",\n};',
        'const protocolColor: Record<string, string> = {\n  vless: "#8b35ff",\n  vmess: "#168cff",\n  trojan: "#b98aff",\n};',
        "protocol palette",
    ),
    (
        '<div className="relative min-h-screen overflow-x-hidden bg-bg pb-16">',
        '<div className="pompnet-subscription relative min-h-screen overflow-x-hidden bg-bg pb-16">',
        "subscription page root",
    ),
    (
        '<div className="font-heading text-2xl leading-tight">SideRail</div>\n              <div className="truncate text-sm font-base text-text/60">{user.email}</div>',
        '<div className="font-heading text-xl leading-tight sm:text-2xl">POMP NET MOHAMMAD</div>\n              <div className="mt-1 text-[10px] font-heading font-bold tracking-[.18em] text-main">SUPER JINX · POWERED BY SideRail</div>\n              <div className="mt-1 truncate text-sm font-base text-text/60">{user.email}</div>',
        "subscription brand header",
    ),
    ('accent="#a3e635"', 'accent="#8b35ff"', "download stat accent"),
    ('accent="#7dd3fc"', 'accent="#168cff"', "upload stat accent"),
    ('accent="#38bdf8"', 'accent="#8b35ff"', "expiry stat accent"),
    ('accent="#fbbf24"', 'accent="#168cff"', "config count accent"),
    ('stopColor="#a3e635"', 'stopColor="#8b35ff"', "download chart fill"),
    ('stopColor="#7dd3fc"', 'stopColor="#168cff"', "upload chart fill"),
    ('stroke="#4d7c0f"', 'stroke="#8b35ff"', "download chart stroke"),
    ('stroke="#0369a1"', 'stroke="#168cff"', "upload chart stroke"),
    ('<span className="h-2 w-2 rounded-full bg-[#a3e635]" />', '<span className="h-2 w-2 rounded-full bg-[#8b35ff]" />', "download chart legend"),
    ('<span className="h-2 w-2 rounded-full bg-[#7dd3fc]" />', '<span className="h-2 w-2 rounded-full bg-[#168cff]" />', "upload chart legend"),
    ('border: "2px solid #000",\n                            borderRadius: 8,\n                            background: "#fff",\n                            color: "#000",',
     'border: "1px solid rgba(139,53,255,.45)",\n                            borderRadius: 12,\n                            background: "#100e1a",\n                            color: "#f4f0ff",',
     "chart tooltip theme"),
]

for old, new, label in replacements:
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit(f"Subscription patch anchor missing: {label}")

p.write_text(s, encoding="utf-8")
print("POMP NET / SUPER JINX subscription UI patch applied")
