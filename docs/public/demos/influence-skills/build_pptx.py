#!/usr/bin/env python3
"""Convert index.html (Liquid Glass deck) into an editable PowerPoint file.

Each slide gets a rendered background (aurora blobs, grain, glass orbs). Glass
cards, circles, icons and text are native PowerPoint objects positioned from
the measured browser layout. Speaker notes are carried over.

Usage: python3 build_pptx.py [output.pptx]
Needs: python-pptx, playwright (+ a Chromium/Chrome binary), lxml.
"""
import asyncio
import copy
import io
import os
import re
import sys

from lxml import etree
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.oxml.ns import qn
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "index.html")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Influence-Skills-Liquid.pptx")
CHROME = os.environ.get("CHROME_PATH", "/usr/local/bin/google-chrome")
FONT = "Arial"
PX = 9525  # EMU per CSS px (1280x720 canvas == 13.333in x 7.5in)
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

EXTRACT_JS = r"""
(i) => {
  document.getElementById('cap')?.remove();
  const src = document.querySelectorAll('#sorter .sort-item')[i].querySelector('.slide');
  const cap = document.createElement('div');
  cap.id = 'cap';
  cap.style.cssText = 'position:fixed;left:0;top:0;width:1280px;height:720px;z-index:99999;overflow:hidden;background:#000';
  const sl = src.cloneNode(true);
  sl.style.position = 'absolute'; sl.style.inset = '0';
  cap.appendChild(sl);
  document.body.appendChild(cap);

  const root = getComputedStyle(document.documentElement);
  const accent = root.getPropertyValue('--accent').trim();
  const accent2 = root.getPropertyValue('--accent2').trim();
  const num = v => parseFloat(v) || 0;
  const items = [];
  const hasDirectText = el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const isCand = el => hasDirectText(el) && getComputedStyle(el).display !== 'inline';
  const parseColor = c => {
    const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(s => parseFloat(s));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };

  for (const el of sl.querySelectorAll('*')) {
    if (el.closest('.bg') || el.classList.contains('grain') || el.classList.contains('orb')) continue;
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();

    if (el.tagName.toLowerCase() === 'svg') {
      const use = el.querySelector('use');
      if (use) items.push({ t: 'icon', sym: (use.getAttribute('href') || '').replace('#i-', ''),
        color: cs.color, x: r.left, y: r.top, w: r.width, h: r.height });
      continue;
    }

    let kind = null;
    if (el.classList.contains('glass')) kind = el.classList.contains('tint') ? 'tint' : el.classList.contains('dim') ? 'dim' : 'glass';
    else if (el.classList.contains('num')) kind = 'num';
    else if (el.classList.contains('ico')) kind = 'ico';
    else if (el.classList.contains('timer')) kind = 'timer';
    else if (el.classList.contains('gauge')) kind = 'gauge';
    else if (el.classList.contains('band')) kind = 'band';
    else if (el.classList.contains('dot')) kind = 'dot';
    if (kind) {
      const rad = Math.min(num(cs.borderTopLeftRadius), Math.min(r.width, r.height) / 2);
      items.push({ t: 'shape', kind, x: r.left, y: r.top, w: r.width, h: r.height, rad });
    }

    if (el.classList.contains('flow')) {
      items.push({ t: 'line', x: r.left + r.width * 0.05, y: r.top + 56 - 2, w: r.width * 0.9, h: 4 });
    }
    if (el.matches('.blist li')) {
      const fs = num(cs.fontSize);
      items.push({ t: 'bullet', x: r.left, y: r.top + 11, d: 10 });
    }

    if (isCand(el) || (hasDirectText(el) && !(() => {
        for (let p = el.parentElement; p && p !== sl; p = p.parentElement) if (isCand(p)) return true; return false; })())) {
      const blk = cs.display !== 'inline' ? el : (() => { let p = el.parentElement; while (p && getComputedStyle(p).display === 'inline') p = p.parentElement; return p; })();
      const bcs = getComputedStyle(blk), br = blk.getBoundingClientRect();
      const cl = br.left + num(bcs.paddingLeft) + num(bcs.borderLeftWidth);
      const cw = br.width - num(bcs.paddingLeft) - num(bcs.paddingRight) - num(bcs.borderLeftWidth) - num(bcs.borderRightWidth);

      const runs = [];
      const rects = [];
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      while (tw.nextNode()) {
        const tn = tw.currentNode;
        if (!tn.textContent.trim() && !runs.length) continue;
        let skip = false;
        for (let p = tn.parentElement; p && p !== el; p = p.parentElement) if (isCand(p)) { skip = true; break; }
        if (skip) continue;
        if (tn.textContent.trim()) {
          const rg = document.createRange(); rg.selectNodeContents(tn);
          for (const q of rg.getClientRects()) if (q.width > 1 && q.height > 1) rects.push(q);
        }
        const pe = tn.parentElement, pcs = getComputedStyle(pe);
        const col = parseColor(pcs.color) || { r: 255, g: 255, b: 255, a: 1 };
        let txt = tn.textContent.replace(/\s+/g, ' ');
        if (bcs.textTransform === 'uppercase') txt = txt.toUpperCase();
        runs.push({ text: txt, size: num(pcs.fontSize), bold: num(pcs.fontWeight) >= 600,
          italic: pcs.fontStyle === 'italic', color: col, grad: !!pe.closest('.grad'),
          spc: pcs.letterSpacing === 'normal' ? 0 : num(pcs.letterSpacing) });
      }
      if (!runs.length) continue;
      runs[0].text = runs[0].text.replace(/^\s+/, '');
      runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, '');

      if (!rects.length) continue;
      const size = num(cs.fontSize);
      const lh = cs.lineHeight === 'normal' ? size * 1.2 : num(cs.lineHeight);
      const lineTops = [...new Set(rects.map(q => Math.round(q.top / (size * 0.6))))];
      const lines = lineTops.length;
      const first = rects.reduce((a, b) => (b.top < a.top ? b : a));
      const align = cs.textAlign === 'center' ? 'ctr' : (cs.textAlign === 'right' || cs.textAlign === 'end') ? 'r' : 'l';
      let x, w;
      if (align === 'ctr') { x = cl; w = cw; }
      else if (lines === 1) {
        x = Math.min(...rects.map(q => q.left));
        w = Math.max(...rects.map(q => q.right)) - x;
      } else {
        x = Math.min(...rects.map(q => q.left));
        const er = el.getBoundingClientRect();
        const right = cs.display !== 'inline' ? er.right - num(cs.paddingRight) : cl + cw;
        w = right - x;
      }
      const cy = first.top + first.height / 2;
      items.push({ t: 'text', x, w, y: cy - lh / 2, lh, lines, align, runs,
        nowrap: lines === 1, cx: cl + cw / 2 });
    }
  }
  return { items, accent, accent2 };
}
"""

BG_JS = r"""
() => { const c = document.querySelector('#cap .content'); if (c) c.style.visibility = 'hidden'; }
"""

def hexof(c):
    return "%02X%02X%02X" % (round(c["r"]), round(c["g"]), round(c["b"]))


def el(tag, **attrs):
    e = etree.SubElement(etree.Element("dummy"), "{%s}%s" % (A, tag))
    for k, v in attrs.items():
        e.set(k, str(v))
    return e


def clr(hexv, alpha=None):
    c = el("srgbClr", val=hexv)
    if alpha is not None and alpha < 100:
        a = etree.SubElement(c, "{%s}alpha" % A)
        a.set("val", str(int(alpha * 1000)))
    return c


def grad(stops, ang):
    g = el("gradFill", rotWithShape="1")
    lst = etree.SubElement(g, "{%s}gsLst" % A)
    for pos, hx, al in stops:
        gs = etree.SubElement(lst, "{%s}gs" % A)
        gs.set("pos", str(int(pos * 1000)))
        gs.append(clr(hx, al))
    lin = etree.SubElement(g, "{%s}lin" % A)
    lin.set("ang", str(int(ang * 60000)))
    lin.set("scaled", "0")
    return g


def solid(hx, al=None):
    s = el("solidFill")
    s.append(clr(hx, al))
    return s


def no_fill():
    return el("noFill")


FILLS = {
    "glass": ([(0, "FFFFFF", 26), (55, "FFFFFF", 9), (100, "FFFFFF", 15)], 50),
    "tint": ([(0, "FFFFFF", 36), (60, "FFFFFF", 13), (100, "FFFFFF", 21)], 50),
    "dim": ([(0, "FFFFFF", 16), (60, "FFFFFF", 6), (100, "FFFFFF", 9)], 50),
    "num": ([(0, "FFFFFF", 58), (100, "FFFFFF", 16)], 50),
    "ico": ([(0, "FFFFFF", 52), (100, "FFFFFF", 14)], 50),
    "timer": ([(0, "FFFFFF", 42), (100, "FFFFFF", 16)], 50),
}


def style_shape(shape, spec, pal):
    sp = shape._element.spPr
    for tag in ("solidFill", "gradFill", "noFill", "ln", "effectLst"):
        for e in sp.findall(qn("a:" + tag)):
            sp.remove(e)
    kind = spec["kind"]
    if kind in FILLS:
        stops, ang = FILLS[kind]
        sp.append(grad(stops, ang))
    elif kind == "gauge":
        sp.append(solid("FFFFFF", 16))
    elif kind == "band":
        sp.append(grad([(0, pal["accent2"], 95), (100, pal["accent"], 95)], 0))
    elif kind in ("dot", "bdot"):
        sp.append(solid("FFFFFF", 100))
    elif kind == "line":
        sp.append(grad([(0, pal["b3"], 90), (50, pal["accent2"], 95), (100, pal["b1"], 90)], 0))

    ln = etree.SubElement(sp, qn("a:ln"))
    if kind in ("glass", "tint", "dim", "timer"):
        ln.set("w", str(int(1.4 * PX * 0.75 * 1.0)))
        ln.append(grad([(0, "FFFFFF", 80), (32, "FFFFFF", 14), (62, "FFFFFF", 10), (100, "FFFFFF", 60)], 50))
    elif kind in ("num", "ico"):
        ln.set("w", str(int(1.4 * PX * 0.75)))
        ln.append(solid("FFFFFF", 38))
    elif kind == "dot":
        ln.set("w", str(int(3 * PX * 0.75)))
        ln.append(solid("FFFFFF", 30))
    else:
        ln.append(no_fill())
    etree.SubElement(sp, qn("a:effectLst"))
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def add_shape(slide, spec, pal):
    from pptx.enum.shapes import MSO_SHAPE
    x, y, w, h = spec["x"], spec["y"], spec["w"], spec["h"]
    kind = spec["kind"]
    if kind in ("num", "ico", "dot", "bdot"):
        shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(int(x * PX)), Emu(int(y * PX)), Emu(int(w * PX)), Emu(int(h * PX)))
    else:
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x * PX)), Emu(int(y * PX)), Emu(int(w * PX)), Emu(int(h * PX)))
        rad = spec.get("rad", 0)
        adj = 0 if min(w, h) <= 0 else max(0.0, min(0.5, rad / min(w, h)))
        shp.adjustments[0] = adj
    style_shape(shp, spec, pal)
    return shp


def add_text(slide, spec, pal):
    pad = max(24, spec["w"] * 0.22) if spec["nowrap"] else 2
    left = spec["x"]
    width = spec["w"] + pad
    if spec["align"] == "ctr" and spec["nowrap"]:
        width = spec["w"] + max(80, spec["w"] * 0.3)
        left = spec["cx"] - width / 2
    height = spec["lh"] * spec["lines"] + 4
    tb = slide.shapes.add_textbox(Emu(int(left * PX)), Emu(int(spec["y"] * PX)), Emu(int(width * PX)), Emu(int(height * PX)))
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = not spec["nowrap"]
    bp = tf._txBody.find(qn("a:bodyPr"))
    for ch in list(bp):
        bp.remove(ch)
    etree.SubElement(bp, qn("a:noAutofit"))
    bp.set("anchor", "t")
    p = tf.paragraphs[0]
    pPr = p._p.get_or_add_pPr()
    pPr.set("algn", spec["align"])
    p.line_spacing = Pt(spec["lh"] * 0.75)
    for r in spec["runs"]:
        if not r["text"]:
            continue
        run = p.add_run()
        run.text = r["text"]
        f = run.font
        f.size = Pt(round(r["size"] * 0.75 * 2) / 2)
        f.bold = r["bold"]
        f.italic = r["italic"]
        f.name = FONT
        c = dict(r["color"])
        if r["spc"] > 0 and not r["grad"] and c["a"] < 0.999:
            bg = (30, 28, 70)
            c = {"r": c["r"] * c["a"] + bg[0] * (1 - c["a"]), "g": c["g"] * c["a"] + bg[1] * (1 - c["a"]),
                 "b": c["b"] * c["a"] + bg[2] * (1 - c["a"]), "a": 1}
        f.color.rgb = __import__("pptx").dml.color.RGBColor.from_string(hexof(c))
        rPr = run._r.get_or_add_rPr()
        sf = rPr.find(qn("a:solidFill"))
        if r["grad"]:
            g = grad([(0, "FFFFFF", None), (55, pal["accent2"], None), (100, pal["accent"], None)], 0)
            rPr.replace(sf, g)
        elif c["a"] < 0.999:
            ac = etree.SubElement(sf.find(qn("a:srgbClr")), qn("a:alpha"))
            ac.set("val", str(int(c["a"] * 100000)))
        if r["spc"]:
            rPr.set("spc", str(int(r["spc"] * 0.75 * 100)))
    return tb


def add_fade(slide):
    sld = slide._element
    tr = etree.Element(qn("p:transition"))
    tr.set("spd", "med")
    etree.SubElement(tr, qn("p:fade"))
    clr_map = sld.find(qn("p:clrMapOvr"))
    if clr_map is not None:
        clr_map.addnext(tr)
    else:
        sld.find(qn("p:cSld")).addnext(tr)


async def render_icon(page, cache, sym, color):
    key = (sym, color)
    if key in cache:
        return cache[key]
    inner = await page.evaluate("(s)=>document.getElementById('i-'+s).innerHTML", sym)
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color)
    col = "rgb(%s,%s,%s)" % m.groups() if m else "#fff"
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="192" height="192" fill="none" '
           'stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (col, inner))
    ip = await page.context.new_page()
    await ip.set_viewport_size({"width": 192, "height": 192})
    await ip.set_content('<body style="margin:0;background:transparent">%s</body>' % svg)
    png = await ip.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 192, "height": 192})
    await ip.close()
    cache[key] = png
    return png


async def main():
    prs = Presentation()
    prs.slide_width = Emu(1280 * PX)
    prs.slide_height = Emu(720 * PX)
    blank = prs.slide_layouts[6]
    prs.core_properties.title = "Influencing Without Authority"
    prs.core_properties.subject = "Influence Skills"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        page = await ctx.new_page()
        await page.goto("file://" + HTML)
        await page.wait_for_timeout(1500)
        total = await page.evaluate("document.querySelectorAll('#sorter .sort-item').length")
        root_vars = await page.evaluate("""() => { const s = getComputedStyle(document.documentElement);
          return {b1:s.getPropertyValue('--b1').trim(), b3:s.getPropertyValue('--b3').trim(),
                  accent:s.getPropertyValue('--accent').trim(), accent2:s.getPropertyValue('--accent2').trim()} }""")
        pal = {k: v.lstrip("#").upper() for k, v in root_vars.items()}
        icon_cache = {}

        for i in range(total):
            data = await page.evaluate(EXTRACT_JS, i)
            await page.evaluate(BG_JS)
            await page.wait_for_timeout(120)
            cap = await page.query_selector("#cap")
            jpg = await cap.screenshot(type="jpeg", quality=92)
            await page.evaluate(
                "()=>{const c=document.querySelector('#cap .content'); if(c) c.style.visibility='visible'}")

            slide = prs.slides.add_slide(blank)
            slide.shapes.add_picture(io.BytesIO(jpg), 0, 0, prs.slide_width, prs.slide_height)
            for it in data["items"]:
                t = it["t"]
                if t == "shape":
                    add_shape(slide, it, pal)
                elif t == "line":
                    add_shape(slide, {"kind": "line", "x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"], "rad": 2}, pal)
                elif t == "bullet":
                    add_shape(slide, {"kind": "bdot", "x": it["x"], "y": it["y"], "w": it["d"], "h": it["d"]}, pal)
                elif t == "icon":
                    png = await render_icon(page, icon_cache, it["sym"], it["color"])
                    slide.shapes.add_picture(io.BytesIO(png), Emu(int(it["x"] * PX)), Emu(int(it["y"] * PX)),
                                             Emu(int(it["w"] * PX)), Emu(int(it["h"] * PX)))
                elif t == "text":
                    add_text(slide, it, pal)
            add_fade(slide)
            print("slide", i + 1, len(data["items"]), "items")
        await page.evaluate("document.getElementById('cap')?.remove()")
        notes_by_slide = await page.evaluate("window.__deckNotes || []")
        for s, n in zip(prs.slides, notes_by_slide):
            if n:
                s.notes_slide.notes_text_frame.text = "\n".join(n)
        await browser.close()
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    asyncio.run(main())
