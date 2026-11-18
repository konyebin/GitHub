#!/usr/bin/env python3
"""Build a simple, flat "Influencing Without Authority" deck as a native .pptx.

Style: off-white background, white cards with thin coloured outlines, coloured
number tabs and serif headings. Everything is an editable PowerPoint object and
speaker notes are included. No browser needed.

Setup:  pip install python-pptx
Run:    python3 build_basic_pptx.py            (writes Influence-Skills-Basic.pptx next to this file)
        python3 build_basic_pptx.py ~/Desktop/MyDeck.pptx
"""
import os
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Influence-Skills-Basic.pptx")

PX = 9525  # EMU per px; slide is 1280 x 720 px (13.333 x 7.5 in)
HEAD = "Georgia"
BODY = "Arial"

BG = "FAFAFA"
INK = "2B2B2B"
GRAY = "5A5A5A"
LIGHT = "E3E3E3"
BLUE = "1B8FCB"
GREEN, ORANGE, DGREEN, YELLOW, PURPLE, RED = "14B06C", "EE6A1F", "0B8140", "E8B400", "6B21A8", "C62828"
CYCLE = [GREEN, ORANGE, DGREEN, YELLOW, PURPLE, RED]


def rgb(h):
    return RGBColor.from_string(h)


def E(v):
    return Emu(int(v * PX))


def strip_style(shape):
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def rect(slide, x, y, w, h, fill=None, line=None, line_w=1.5, radius=6):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, E(x), E(y), E(w), E(h))
    strip_style(shp)
    shp.adjustments[0] = min(0.5, radius / max(1, min(w, h)))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
    else:
        shp.line.fill.background()
    return shp


def text(slide, x, y, w, h, paras, size=18, color=INK, font=BODY, bold=False, italic=False,
         align="l", anchor="t", spacing=1.15, bullet=None, space_after=0):
    """paras: str | list[str | list[(text, {overrides})]]"""
    tb = slide.shapes.add_textbox(E(x), E(y), E(w), E(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    bp = tf._txBody.find(qn("a:bodyPr"))
    for ch in list(bp):
        bp.remove(ch)
    etree.SubElement(bp, qn("a:noAutofit"))
    bp.set("anchor", {"t": "t", "m": "ctr", "b": "b"}[anchor])
    if isinstance(paras, str):
        paras = [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        pPr = p._p.get_or_add_pPr()
        pPr.set("algn", align)
        if bullet:
            pPr.set("marL", str(int(26 * PX)))
            pPr.set("indent", str(int(-26 * PX)))
            bu = etree.SubElement(pPr, qn("a:buFont"))
            bu.set("typeface", "Arial")
            if bullet == "num":
                etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
            else:
                etree.SubElement(pPr, qn("a:buChar")).set("char", "•")
        runs = [(para, {})] if isinstance(para, str) else para
        for t, o in runs:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", italic)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def card(slide, x, y, w, h, color, num=None, tab_y=22):
    rect(slide, x, y, w, h, fill="FFFFFF", line=color, line_w=1.5, radius=6)
    if num is not None:
        tab = rect(slide, x - 12, y + tab_y, 58, 40, fill=color, radius=10)
        tf = tab.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(num)
        r.font.size = Pt(18)
        r.font.bold = True
        r.font.name = BODY
        r.font.color.rgb = rgb("FFFFFF")
        tf._txBody.find(qn("a:bodyPr")).set("anchor", "ctr")


def heading(slide, x, y, w, label, color, size=22, h=40, tab_y=22):
    text(slide, x + 62, y + tab_y - 4, w - 78, h, label, size=size, color=color, font=HEAD, anchor="m" if h <= 48 else "t")


def divider(slide, x, y, w):
    ln = rect(slide, x, y, w, 1.2, fill=LIGHT, radius=0)
    return ln


def slide_title(slide, label, sub=None):
    text(slide, 64, 36, 1152, 60, label, size=32, color=INK, font=HEAD, anchor="m")
    if sub:
        text(slide, 64, 96, 1152, 30, sub, size=17, color=GRAY)


def footer(slide):
    text(slide, 880, 668, 336, 28, "Influence Skills", size=15, color=BLUE, bold=True, align="r")


NOTES = {
    1: ["Ask the group for their thoughts: What does influence without authority mean?"],
    2: ["We don't always have the authority to make decisions or determine someone else's priorities.",
        "But in our roles, we're constantly working through other people to accomplish something.",
        "Whether that's getting internal alignment, encouraging customer adoption, or partnering with another team, our ability to influence can determine whether we move forward or get stuck."],
    3: ["Credibility Example:",
        "Come to a customer conversation prepared with usage data, renewal history, product information, and specific recommendations.",
        "Follow through on commitments and be someone colleagues can depend on.",
        "Understanding Example:",
        "Before approaching your field rep about an expansion opportunity, understand their current priorities, pipeline, and workload.",
        "Before recommending an adoption strategy to a customer, understand what's preventing teachers or students from using IXL.",
        "Mutual Value Example:",
        "Instead of simply presenting an opportunity to increase licenses, connect the recommendation to increased student access, stronger implementation, and the customer's implementation goals.",
        "When partnering with your ESC, demonstrate how working together can create a better customer experience while supporting shared business goals.",
        "\u201COne thing I've learned is that having the right information isn't always enough. People need to trust your judgment, feel like you understand their situation, and see how your recommendation benefits them. That's what turns a conversation into collaboration.\u201D"],
    4: ["Sometimes the difference between getting buy-in and getting resistance is how we approach the conversation. Instead of immediately presenting our solution, we can create space for the other person to share their perspective. Then we can connect our recommendation to something they already care about.",
        "You don't have to convince someone of everything at once. Sometimes the goal is simply getting agreement on the next step.",
        "Can anyone think of an additional examples?"],
    5: ["Let's put this into practice. Imagine you're working with a customer who isn't fully implementing IXL. You recognize the opportunity, but you can't make the administrator prioritize implementation or make teachers use the platform.",
        "\u201CHow would you influence the situation?\u201D",
        "After the group shares, ask:",
        "\u201CWhat would be the difference between trying to convince this customer and actually influencing them?\u201D",
        "Your closing observation:",
        "\u201CNotice how many of these approaches start with understanding the other person's challenges rather than immediately presenting a solution. That's really what influence is about.\u201D"],
    8: ["\u201CLeadership isn't always about having the authority to make a decision. Sometimes it's about earning enough trust, understanding, and alignment that people choose to move forward with you.\u201D"],
}


def s01(s):
    rect(s, 140, 170, 1000, 340, fill="FFFFFF", line=GREEN, line_w=1.5)
    rect(s, 128, 200, 58, 40, fill=GREEN, radius=10)
    text(s, 230, 205, 800, 30, "INFLUENCE SKILLS", size=15, color=GREEN, bold=True)
    text(s, 230, 260, 840, 190, "Influencing Without Authority", size=50, color=INK, font=HEAD, spacing=1.05)


def s02(s):
    slide_title(s, "What does influence without authority mean?")
    rect(s, 64, 120, 1152, 130, fill="FFFFFF", line=GREEN)
    text(s, 96, 120, 1088, 130, "Influence is the ability to shape someone's thinking or actions without relying on your title, position, or control.",
         size=24, anchor="m", spacing=1.2)
    text(s, 64, 285, 400, 28, "Examples", size=16, color=GRAY, bold=True)
    ex = ["You need a partner's cooperation, but you aren't their manager.",
          "You need another team to prioritize an issue affecting your customer.",
          "You want a customer to consider a different approach to implementation, adoption, or renewal."]
    for i, t in enumerate(ex):
        x = 64 + i * 394
        col = [ORANGE, DGREEN, PURPLE][i]
        card(s, x, 325, 364, 260, col, num=i + 1)
        text(s, x + 28, 395, 308, 140, t, size=19, spacing=1.2)


def s03(s):
    slide_title(s, "Setting Yourself Up For Success")
    items = [("Credibility", "Demonstrate that you're prepared, reliable, knowledgeable, and focused on solving the problem.", GREEN),
             ("Understanding", "Learn what matters to the other person, what constraints they face, and what success looks like from their perspective.", ORANGE),
             ("Mutual value", "Connect your recommendation to an outcome that matters to both parties.", PURPLE)]
    for i, (h, d, col) in enumerate(items):
        x = 64 + i * 394
        card(s, x, 130, 364, 420, col, num=i + 1)
        heading(s, x, 130, 364, h, col, size=26)
        divider(s, x + 28, 200, 308)
        text(s, x + 28, 222, 308, 300, d, size=20, color=GRAY, spacing=1.25)


def s04(s):
    slide_title(s, "Getting Buy-in")
    rows = [("Ask before advocating", "Here's what we need to do.", "What challenges are you currently running into?"),
            ("Connect to shared goals", "This is important to my account.", "Here's how this could improve the customer experience and help us achieve our goals."),
            ("Use evidence and examples", "I think this is the right move.", "Based on their usage trends and current licenses, here's an opportunity I noticed."),
            ("Make the next step easy", "Can you take care of this?", "Would you be open to connecting for 15 minutes to talk through the opportunity?")]
    for i, (st, old, new) in enumerate(rows):
        x = 64 + (i % 2) * 592
        y = 118 + (i // 2) * 266
        col = [GREEN, ORANGE, DGREEN, PURPLE][i]
        card(s, x, y, 560, 250, col, num=i + 1)
        heading(s, x, y, 560, st, col, size=22)
        divider(s, x + 28, y + 78, 504)
        text(s, x + 28, y + 92, 504, 20, "INSTEAD OF", size=11, color=GRAY, bold=True)
        text(s, x + 28, y + 112, 504, 50, "\u201C" + old + "\u201D", size=16, color=GRAY, italic=True)
        text(s, x + 28, y + 160, 504, 20, "TRY", size=11, color=BLUE, bold=True)
        text(s, x + 28, y + 180, 504, 60, "\u201C" + new + "\u201D", size=16, color=INK)


def s05(s):
    slide_title(s, "Let\u2019s try")
    card(s, 64, 120, 560, 500, GREEN, num=1)
    heading(s, 64, 120, 560, "The situation", GREEN, size=24)
    divider(s, 92, 190, 504)
    text(s, 92, 208, 504, 70, "You've identified an opportunity to improve a customer's IXL adoption. However:", size=17, color=GRAY, spacing=1.2)
    text(s, 92, 290, 504, 320,
         ["The customer administrator is overwhelmed.",
          "Teachers aren't consistently using the platform.",
          "The administrator isn't prioritizing implementation.",
          [("You recognize the opportunity, but you don't have authority over the administrator or the teachers.", {"bold": True})]],
         size=17, bullet="dot", spacing=1.2, space_after=10)
    card(s, 656, 120, 560, 500, ORANGE, num=2)
    heading(s, 656, 120, 560, "Your challenge", ORANGE, size=24)
    divider(s, 684, 190, 504)
    text(s, 684, 208, 504, 70, "As a group, brainstorm how you could influence the situation.", size=17, bold=True, spacing=1.2)
    text(s, 684, 290, 504, 320,
         ["What questions would you ask to better understand the situation?",
          "How would you demonstrate value without making the customer feel pressured?",
          "What's one small next step you could get them to agree to?"],
         size=17, bullet="num", spacing=1.2, space_after=12)


def s06(s):
    slide_title(s, "5 Reminders for your next conversation")
    r = [("Lead with curiosity", "Ask questions before offering solutions"),
         ("Understand their perspective", "Consider their priorities, challenges, and other demands"),
         ("Connect to shared goals", "Show the value in working together"),
         ("Bring something to the table", "Use relevant information and examples to build credibility"),
         ("Make the next step easy", "Start with one actionable step")]
    for i, (h, d) in enumerate(r):
        y = 116 + i * 100
        col = CYCLE[i]
        card(s, 64, y, 1152, 86, col, num=i + 1, tab_y=23)
        text(s, 140, y, 440, 86, h, size=22, color=col, font=HEAD, anchor="m")
        text(s, 600, y, 580, 86, d, size=18, color=GRAY, anchor="m")


def s07(s):
    slide_title(s, "Challenge")
    card(s, 64, 150, 1152, 330, PURPLE, num=1, tab_y=26)
    text(s, 140, 160, 600, 50, "This week", size=26, color=PURPLE, font=HEAD, anchor="m")
    divider(s, 92, 230, 1096)
    text(s, 92, 262, 1096, 200, "This week, identify one conversation where you need someone\u2019s buy-in or support.",
         size=34, spacing=1.2)


def s08(s):
    slide_title(s, "5 Reminders for your next conversation", "The next time you need buy in, ask the following questions:")
    q = [("What matters to them?", "Define the concrete ask in one sentence to guide every follow-up."),
         ("What shared goal can we connect around?", "Pin the stakeholder\u2019s top two motivations to align your ask."),
         ("What evidence or credibility can I bring?", "Select one persuasion lever and draft the opening line."),
         ("What small next step can I propose?", "Specify a small, time-limited ask with a reciprocal benefit.")]
    for i, (h, d) in enumerate(q):
        x = 64 + (i % 2) * 592
        y = 150 + (i // 2) * 245
        col = [GREEN, ORANGE, DGREEN, YELLOW][i]
        card(s, x, y, 560, 225, col, num=i + 1)
        heading(s, x, y, 560, h, col, size=22, h=70)
        text(s, x + 28, y + 118, 504, 90, d, size=18, color=GRAY, spacing=1.2)


def s09(s):
    slide_title(s, "Influence Mastery")
    card(s, 64, 120, 1152, 230, GREEN)
    text(s, 96, 120, 1088, 230,
         "Influence without authority is a strategic muscle you can build. Levers\u2014reciprocity, credibility, scarcity, and social proof\u2014drive persuasive requests without formal power. Use the five-step prep and the lightweight metrics to plan, test, and learn from each cross-functional ask.",
         size=22, anchor="m", spacing=1.3)
    text(s, 64, 385, 400, 26, "The four levers", size=16, color=GRAY, bold=True)
    for i, (name, col) in enumerate([("Reciprocity", ORANGE), ("Credibility", DGREEN), ("Scarcity", PURPLE), ("Social proof", RED)]):
        x = 64 + i * 296
        rect(s, x, 425, 272, 120, fill="FFFFFF", line=col)
        text(s, x, 425, 272, 120, name, size=24, color=col, font=HEAD, align="ctr", anchor="m")


def s10(s):
    slide_title(s, "Influence Metrics", "Three simple metrics to gauge whether an influence attempt sticks and where to improve.")
    m = [("Conversion rate", "38%", "Conversion rate (cross-team asks); target 30\u201350%.", GREEN),
         ("Time-to-agreement", "7 days", "Time-to-agreement (first request to commitment); aim to reduce by 25% over three attempts.", ORANGE),
         ("Collaboration durability", "1+", "Collaboration durability (repeat interactions or voluntary contributions next quarter); target at least one repeat contribution.", PURPLE)]
    for i, (h, big, d, col) in enumerate(m):
        x = 64 + i * 394
        card(s, x, 150, 364, 440, col, num=i + 1)
        heading(s, x, 150, 364, h, col, size=18)
        text(s, x + 28, 225, 308, 110, big, size=64, color=col, font=HEAD, anchor="m")
        divider(s, x + 28, 352, 308)
        text(s, x + 28, 374, 308, 200, d, size=17, color=GRAY, spacing=1.25)


def s11(s):
    slide_title(s, "Four ways to influence others")
    st = [("Ask before advocating", "Identify the exact ask and the stakeholder's likely priorities; draft a concise one-paragraph request."),
          ("Diagnose", "Map incentives and constraints (time, KPIs, career goals) that drive the stakeholder."),
          ("Frame", "Open with their priorities, present the ask as low-risk/high-value, and apply one lever (e.g., reciprocity)."),
          ("Offer", "Present a clear, limited ask and explicit benefit (e.g., one-hour review meeting; credit your team in release notes)."),
          ("Follow-up", "Document agreements, thank collaborators publicly, and deliver on promised reciprocation.")]
    for i, (h, d) in enumerate(st):
        x = 64 + (i % 3) * 394
        y = 118 + (i // 3) * 255
        col = CYCLE[i]
        card(s, x, y, 364, 235, col, num=i + 1)
        heading(s, x, y, 364, h, col, size=22)
        divider(s, x + 28, y + 78, 308)
        text(s, x + 28, y + 94, 308, 130, d, size=16, color=GRAY, spacing=1.25)


def s12(s):
    rect(s, 240, 200, 800, 280, fill="FFFFFF", line=GREEN)
    text(s, 240, 225, 800, 120, "Thanks!", size=60, color=GREEN, font=HEAD, align="ctr", anchor="m")
    text(s, 240, 350, 800, 60, "Do you have any questions?", size=26, color=GRAY, align="ctr", anchor="m")


BUILDERS = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12]


def main():
    prs = Presentation()
    prs.slide_width = E(1280)
    prs.slide_height = E(720)
    prs.core_properties.title = "Influencing Without Authority"
    blank = prs.slide_layouts[6]
    for n, build in enumerate(BUILDERS, 1):
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(BG)
        build(s)
        footer(s)
        if n in NOTES:
            s.notes_slide.notes_text_frame.text = "\n".join(NOTES[n])
    prs.save(OUT)
    print("Saved", OUT)


if __name__ == "__main__":
    main()
