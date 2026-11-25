from pathlib import Path

# Apply the owner's English brand to generated client/profile names only.
# Upstream source headers, license, authorship and About attribution are untouched.
links = Path("apps/server/src/links.ts")
s = links.read_text(encoding="utf-8")
old = '''/** Config / subscription name: 𝗦𝗶𝗱𝗲𝗥𝗮𝗶𝗹 <flag> - <client name> */
export function configName(user: UserWithInbounds, flag?: string): string {
  const f = (flag || "").trim();
  return f
    ? `${toBoldAscii("SideRail")} ${f} - ${toBoldAscii(user.email)}`
    : `${toBoldAscii("SideRail")} - ${toBoldAscii(user.email)}`;
}'''
new = '''/** Config / subscription name: Mohammad Pomp Net | SUPER JINX <flag> - <client name>. */
export function configName(user: UserWithInbounds, flag?: string): string {
  const f = (flag || "").trim();
  const prefix = toBoldAscii("Mohammad Pomp Net | SUPER JINX");
  return f
    ? `${prefix} ${f} - ${toBoldAscii(user.email)}`
    : `${prefix} - ${toBoldAscii(user.email)}`;
}'''
if old not in s:
    raise SystemExit("Expected configName implementation was not found; refusing a partial patch.")
s = s.replace(old, new, 1)
links.write_text(s, encoding="utf-8")

sub = Path("apps/server/src/sub.ts")
s = sub.read_text(encoding="utf-8")
old_title = 'Buffer.from(`SideRail ${data.user.email}`).toString("base64")'
new_title = 'Buffer.from(`Mohammad Pomp Net | SUPER JINX ${data.user.email}`).toString("base64")'
if s.count(old_title) != 2:
    raise SystemExit(f"Expected 2 subscription profile-title occurrences, found {s.count(old_title)}.")
s = s.replace(old_title, new_title)
sub.write_text(s, encoding="utf-8")

formats = Path("apps/server/src/sub-formats.ts")
s = formats.read_text(encoding="utf-8")
old_clash = 'yaml.push(`  - name: SideRail`);'
new_clash = 'yaml.push(`  - name: Mohammad Pomp Net | SUPER JINX`);'
old_singbox = 'tag: "SideRail",'
new_singbox = 'tag: "Mohammad Pomp Net | SUPER JINX",'
if s.count(old_clash) != 1 or s.count(old_singbox) != 1:
    raise SystemExit("Expected Clash and sing-box group labels were not found exactly once.")
s = s.replace(old_clash, new_clash, 1).replace(old_singbox, new_singbox, 1)
formats.write_text(s, encoding="utf-8")

print("POMP NET generated-config branding patch applied.")
