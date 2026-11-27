#!/usr/bin/env python3
"""
外壁塗装・屋根＋助成金 ニッチSEOサイト 静的ジェネレータ

使い方:
  python3 build.py

入力: data/subsidies.csv （元データ: ~/workspace/seo-site-exterior-painting/subsidies-initial.csv）
     千代田区は data/chiyoda-2026.json があればそちらで上書きする（今年度版の公式再確認結果）
出力: index.html / subsidies/index.html / subsidies/<slug>/index.html / alternatives/ / about/

原則:
- 数字はCSV（公式確認済み）にあるものだけを出す。推測で埋めない。
- 提携リンクは貼らない。送客枠は「準備中」のプレースホルダ表示のみ。
- 費用相場の具体額は、出典を確認できる数字がまだ無いため掲載しない。
"""
import csv, html, json, os, re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "subsidies.csv"
CHIYODA_OVERRIDE = ROOT / "data" / "chiyoda-2026.json"

SLUGS = {
    "千代田区": "chiyoda", "港区": "minato", "新宿区": "shinjuku", "渋谷区": "shibuya",
    "世田谷区": "setagaya", "豊島区": "toshima", "練馬区": "nerima", "大田区": "ota",
    "足立区": "adachi", "江戸川区": "edogawa",
    "札幌市": "sapporo", "仙台市": "sendai", "さいたま市": "saitama", "千葉市": "chiba",
    "横浜市": "yokohama", "川崎市": "kawasaki", "名古屋市": "nagoya", "京都市": "kyoto",
    "大阪市": "osaka", "神戸市": "kobe",
}

def esc(s):
    return html.escape((s or "").strip())

def field(v):
    v = (v or "").strip()
    if v in ("", "-", "ー"):
        return "公式ページに外壁塗装向け助成の記載はありませんでした"
    return v

CSS = """
:root{--ink:#1f2937;--muted:#6b7280;--line:#e5e7eb;--bg:#f8fafc;--card:#fff;--accent:#0f766e;--warn:#b45309;--warnbg:#fffbeb;--okbg:#ecfdf5;--nobg:#fef2f2}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif;color:var(--ink);background:var(--bg);line-height:1.75}
header.site{background:#0f3d3a;color:#fff;padding:14px 20px}header.site a{color:#fff;text-decoration:none;font-weight:700}
header.site .tag{display:block;font-weight:400;font-size:13px;opacity:.85}
main{max-width:880px;margin:0 auto;padding:24px 16px 56px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
h1{font-size:26px;line-height:1.4}h2{font-size:20px;border-left:4px solid var(--accent);padding-left:10px;margin-top:32px}
.conclusion{border-radius:12px;padding:16px 20px;font-weight:700;font-size:18px;margin:16px 0}
.conclusion.yes{background:var(--okbg);border:1px solid #a7f3d0}
.conclusion.no{background:var(--nobg);border:1px solid #fecaca}
table{width:100%;border-collapse:collapse;background:#fff}th,td{border:1px solid var(--line);padding:10px 12px;text-align:left;vertical-align:top;font-size:15px}th{width:28%;background:#f1f5f9}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:700}
.badge.yes{background:#d1fae5;color:#065f46}.badge.no{background:#fee2e2;color:#991b1b}
a{color:#0f766e}.small{font-size:13px;color:var(--muted)}
.notice{background:var(--warnbg);border:1px solid #fde68a;border-radius:10px;padding:14px 18px;font-size:14px}
.placeholder{border:2px dashed #cbd5e1;border-radius:10px;padding:16px;text-align:center;color:var(--muted);background:#f8fafc}
ul.citylist{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
ul.citylist li{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
footer{max-width:880px;margin:0 auto;padding:20px 16px 40px;color:var(--muted);font-size:13px;border-top:1px solid var(--line)}
"""

def layout(title, body, depth=0):
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | 外壁塗装ナビ（仮）</title>
<meta name="description" content="{esc(title)}。自治体公式ページで確認した情報だけを、出典と確認日つきで掲載します。">
<meta name="google-site-verification" content="CvFgK5oamyRo5vpC9yJ04DHveJ5tD9HXxCtGN4cvsyQ">
<link rel="stylesheet" href="{prefix}assets/style.css">
<link rel="icon" type="image/svg+xml" href="{prefix}assets/favicon.svg">
</head>
<body>
<header class="site"><a href="{prefix}index.html">外壁塗装ナビ（仮）</a><span class="tag">自治体公式情報で確認した、外壁塗装の助成金と費用の情報整理サイト（プロトタイプ・未公開）</span></header>
<main>
{body}
</main>
<footer>掲載情報は各自治体の公式ページを確認した時点のものです。制度は年度で変わります。申請前に必ず公式ページで最新情報を確認してください。<br><a href="{prefix}about/index.html">このサイトについて（出典方針）</a></footer>
</body>
</html>
"""

def load_rows():
    with open(DATA, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # 千代田区の今年度版上書き（公式再確認が済んだ場合のみファイルが存在する）
    if CHIYODA_OVERRIDE.exists():
        ov = json.loads(CHIYODA_OVERRIDE.read_text(encoding="utf-8"))
        for r in rows:
            if r["自治体名"] == "千代田区":
                r.update(ov)
    return rows

def city_page(r):
    name, pref = r["自治体名"], r["都道府県"]
    yes = r["制度の有無"].strip() == "あり"
    cls = "yes" if yes else "no"
    if yes and ("受付終了" in r["申請時期・受付状況"] or "受付を終了" in r["申請時期・受付状況"]):
        conclusion = f"{name}には助成制度がありますが、今年度分は受付が終了しています（詳細は下記「申請時期・受付状況」）"
    elif yes:
        conclusion = f"{name}には、外壁塗装が対象になり得る助成制度があります（条件つき）"
    else:
        conclusion = f"{name}には、外壁塗装を対象とする助成金は確認できませんでした"
    alt = ""
    if not yes:
        alt = """
<h2>助成金が無い場合に確認したいこと</h2>
<div class="card">
<ul>
<li><strong>一般リフォーム・省エネ・耐震などの制度</strong>：塗装単体は対象外でも、断熱改修などと組み合わせると対象になる制度が自治体にある場合があります。上の「制度名・関連制度」と公式ページを確認してください。</li>
<li><strong>火災保険</strong>：風災などの被害による修理が対象になる場合がありますが、経年劣化による塗り替えは一般に対象外です。契約内容を保険会社に確認してください（適用を断定するものではありません）。</li>
<li><strong>費用を抑える方法</strong>：外壁と屋根を同時に行うと足場代が一度で済みます。複数社から相見積もりを取り、見積もり書の内訳（塗料名・塗布面積・工程）を比べることが基本です。</li>
</ul>
<p><a href="../../alternatives/index.html">「助成金が無い」自治体での代替策まとめ</a></p>
</div>"""
    body = f"""
<p class="small"><a href="../../index.html">トップ</a> ＞ <a href="../index.html">助成金データベース</a> ＞ {esc(pref)} {esc(name)}</p>
<h1>{esc(name)}の外壁塗装助成金・補助金</h1>
<div class="conclusion {cls}">{esc(conclusion)}</div>
<table>
<tr><th>制度名</th><td>{esc(field(r['制度名']))}</td></tr>
<tr><th>対象</th><td>{esc(field(r['対象']))}</td></tr>
<tr><th>補助額・率</th><td>{esc(field(r['補助額・率']))}</td></tr>
<tr><th>主な条件</th><td>{esc(field(r['主な条件']))}</td></tr>
<tr><th>申請時期・受付状況</th><td>{esc(field(r['申請時期・受付状況']))}</td></tr>
<tr><th>公式URL（出典）</th><td><a href="{esc(r['公式URL'])}" rel="noopener" target="_blank">{esc(r['公式URL'])}</a></td></tr>
<tr><th>最終確認日</th><td>{esc(r['確認日'])}</td></tr>
</table>
<h2>読み解きメモ</h2>
<div class="card">{esc(r['備考'])}</div>
{alt}
<h2>見積もりを取る前に</h2>
<div class="placeholder">見積もり比較サービスへの案内は準備中です（提携申請はサイト公開後に行います）。現在はリンクを設置していません。</div>
<div class="notice">注意：制度内容は変更・終了する場合があります。申請前に必ず自治体公式ページで最新情報を確認してください。特に「工事前の申請が必要」な制度では、契約・着工の順番を間違えると対象外になります。</div>
"""
    return layout(f"{name}の外壁塗装助成金・補助金", body, depth=2)

def main():
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    rows = load_rows()
    for r in rows:
        r["_slug"] = SLUGS[r["自治体名"]]
    yes_rows = [r for r in rows if r["制度の有無"].strip() == "あり"]
    no_rows = [r for r in rows if r["制度の有無"].strip() != "あり"]

    # 自治体ページ
    for r in rows:
        d = ROOT / "subsidies" / r["_slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(city_page(r), encoding="utf-8")

    # DBインデックス
    def city_li(r):
        yes = r["制度の有無"].strip() == "あり"
        badge = '<span class="badge yes">制度あり</span>' if yes else '<span class="badge no">制度なし</span>'
        return f'<li><a href="{r["_slug"]}/index.html">{esc(r["都道府県"])} {esc(r["自治体名"])}</a><br>{badge}<br><span class="small">{esc(r["制度名"])}</span></li>'
    idx_body = f"""
<h1>自治体助成金データベース</h1>
<p>初期データとして {len(rows)}自治体（東京都10区＋政令指定都市10市）を、各自治体の公式ページで確認しました。制度ありが {len(yes_rows)}、なしが {len(no_rows)} です。「なし」の自治体では、代替策への案内を各ページに載せています。</p>
<h2>制度がある自治体（{len(yes_rows)}）</h2>
<ul class="citylist">{''.join(city_li(r) for r in yes_rows)}</ul>
<h2>外壁塗装向けの制度が無い自治体（{len(no_rows)}）</h2>
<ul class="citylist">{''.join(city_li(r) for r in no_rows)}</ul>
<p class="small">対象自治体は、検索の反応を見ながら数十自治体まで少しずつ広げる予定です（全国一律には広げません。鮮度確認のコストを管理するためです）。</p>
"""
    (ROOT / "subsidies").mkdir(exist_ok=True)
    (ROOT / "subsidies" / "index.html").write_text(layout("自治体助成金データベース", idx_body, depth=1), encoding="utf-8")

    # トップ
    top_body = f"""
<h1>外壁塗装の「助成金」と「費用」を、公式情報で正直に調べる</h1>
<div class="card">
<p>外壁塗装には、自治体の助成金が<strong>ある自治体と、無い自治体</strong>があります。最初に確認した{len(rows)}自治体では、制度があったのは{len(yes_rows)}つだけでした。</p>
<p>このサイトは、自治体の公式ページで確認できた情報だけを、出典と確認日つきで載せます。無い自治体は「なし」と書き、代わりに使える制度や費用を抑える方法を案内します。</p>
<p><a href="subsidies/index.html">→ 自分の自治体の助成金を調べる（{len(rows)}自治体）</a></p>
</div>
<h2>制度がある自治体（初期データ）</h2>
<ul class="citylist">{''.join(f'<li><a href="subsidies/{r["_slug"]}/index.html">{esc(r["都道府県"])} {esc(r["自治体名"])}</a><br><span class="small">{esc(r["制度名"])}／{esc(r["補助額・率"])}</span></li>' for r in yes_rows)}</ul>
<h2>これから載せる記事</h2>
<div class="card">
<ul>
<li>外壁塗装の費用相場（坪数別）― 出典を確認できる数字だけを使うため、現在は準備中です。具体額を推測で載せることはしません。</li>
<li><a href="alternatives/index.html">助成金が無い自治体で使える制度・代替策まとめ</a></li>
<li>助成金の申請の流れ（工事前の申請が必要な理由）</li>
<li>火災保険が使えるケース・使えないケース</li>
</ul>
</div>
<div class="placeholder">見積もり比較サービスへの案内は準備中です（提携申請後に設置します）。</div>
"""
    (ROOT / "index.html").write_text(layout("トップページ", top_body, depth=0), encoding="utf-8")

    # 代替策ページ
    alt_body = """
<h1>外壁塗装に助成金が無い自治体で、確認したい代替策</h1>
<p>初期データ20自治体のうち15自治体では、外壁塗装を対象とする助成金は確認できませんでした。無いものは無いのですが、次を確認する価値はあります。</p>
<div class="card"><h2>1. 一般リフォーム・省エネ・耐震の制度</h2><p>塗装単体は対象外でも、窓や外壁の断熱改修、耐震改修などと組み合わせる工事が対象になる制度を持つ自治体があります。各自治体ページの「関連制度」と公式ページを確認してください。</p></div>
<div class="card"><h2>2. 都道府県・国の制度</h2><p>市区町村に制度が無くても、都道府県や国の省エネ改修支援の対象になる場合があります。ただし塗装単体が対象になる制度は限られます。公式ページで対象工事を必ず確認してください。</p></div>
<div class="card"><h2>3. 火災保険</h2><p>台風・風災などで外壁や屋根が破損した修理は、契約内容によっては火災保険の対象になる場合があります。一方、経年劣化による塗り替えは一般に対象外です。適用できるかどうかは保険会社への確認が必要です。</p></div>
<div class="card"><h2>4. リフォームローン・融資あっせん</h2><p>助成ではなく低利融資のあっせん制度を持つ自治体もあります（例：江戸川区の住宅リフォーム資金融資あっせん制度は各自治体ページに記載）。金利や条件は公式ページで確認してください。</p></div>
<div class="card"><h2>5. 工事の組み方で費用を抑える</h2><p>外壁と屋根を同時に塗装すると足場を一度で済ませられます。複数社の相見積もりを取り、塗料名・塗布面積・工程（下塗り／中塗り／上塗り）が見積書に明記されているかを比べることが、金額の妥当性を確かめる基本です。</p></div>
<p><a href="../subsidies/index.html">→ 自治体別ページに戻る</a></p>
"""
    (ROOT / "alternatives").mkdir(exist_ok=True)
    (ROOT / "alternatives" / "index.html").write_text(layout("助成金が無い自治体での代替策", alt_body, depth=1), encoding="utf-8")

    # About
    about_body = """
<h1>このサイトについて</h1>
<div class="card">
<h2>出典方針</h2>
<ul>
<li>助成金の情報は、各自治体の公式ページ（公式ドメイン）を実際に開いて確認したものだけを載せます。</li>
<li>全ページに「最終確認日」と公式URLを表示します。</li>
<li>制度が無い自治体は「なし」と明記します。あるように見せる表現はしません。</li>
<li>費用相場などの数字は、出典を明記できるものだけを使います。確認できない数字は載せません。</li>
<li>体験談・施工事例の捏造はしません。</li>
</ul>
<h2>更新方針</h2>
<p>助成金は年度で変わり、予算到達で年度途中に終了することもあります。年度替わり（3〜4月）に全自治体ページを再確認します。</p>
<p class="small">現在はプロトタイプ（未公開）です。運営者情報・特商法表記は、送客開始時に整備します。</p>
</div>
"""
    (ROOT / "about").mkdir(exist_ok=True)
    (ROOT / "about" / "index.html").write_text(layout("このサイトについて", about_body, depth=1), encoding="utf-8")

    # sitemap / robots（公開先は GitHub Pages の想定URL。公開までは参照用）
    base = "https://urumunahu1124.github.io/gaiheki-navi/"
    paths = ["", "subsidies/", "alternatives/", "about/"] + [f"subsidies/{r['_slug']}/" for r in rows]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{base}{p}</loc></url>" for p in paths]
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8")

    print(f"generated: top, db index, {len(rows)} city pages, alternatives, about, sitemap({len(paths)} urls), robots")

if __name__ == "__main__":
    main()
