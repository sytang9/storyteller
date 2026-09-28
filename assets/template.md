---
title: {{The finding, as a plain claim}}
kicker: {{PROJECT · KIND OF REPORT}}
dek: {{One sentence: what we now know and what it means.}}
subtitle: {{Audience}} · updated {{YYYY-MM-DD}}
theme: auto
toc: true
pdf: false
---

## The answer

<div class="answer">
{{1-2 sentences: what we asked, what we found, what you need to decide.}}
</div>

<!-- FIG:overview pipeline -->
*{{Caption: the whole story in one picture; it names each chapter's part in the chapter's words.}}*
<!-- For a system the reader should explore, you may add an interactive map with a MAP:overview marker after the MENU line below (see references/motion.md); the drawn overview stays here. -->

<!-- TL;DR labels that fit the report: results "Where we are / What we did / What's next";
     investigation "What happened / Why / What to fix"; proposal "The problem / The idea / What we ask";
     status "Done / In progress / Next"; engineering record "What we built / What we measured / What's left". -->
<div class="tldr">
  <div><span class="label">{{Where we are}}</span><b>{{key number}}</b><p>{{vs its baseline, one line, at most 20 words}}</p></div>
  <div><span class="label">{{What we did}}</span><b>{{key number}}</b><p>{{one line, at most 20 words}}</p></div>
  <div><span class="label">{{What's next}}</span><b>{{key number or step}}</b><p>{{one line, at most 20 words}}</p></div>
</div>

<!-- MENU -->

<section class="acc-teal" markdown="1">

<p class="chapter-no">01<span>{{Short label}}</span></p>

## {{Story chapter: the takeaway, as a full sentence}}

<!-- FIG:chapter1 scene -->
*{{Caption: the takeaway of this picture, one sentence.}}*

<div class="hero-num"><b>{{the number}}</b><span>{{what it counts, vs its baseline}}</span></div>

**{{Bold lead.}}** {{At most 3 sentences in all, each opening with a bold lead. Define a new term inline: <dfn>Term</dfn>, precise meaning, and an analogy if the reader lacks the concept.}}

<aside class="sidenote">{{Visible side note: the definition, the caveat, or the one supporting number.}}</aside>

<details class="evidence" markdown="1">
<summary>{{Optional kicker: <span class="kick">Unmasked</span>; see references/look.md}} {{What is inside and why to open it, e.g. "How we got 85%: 3 runs, per-run table"}}</summary>

{{Audit material only: method, full tables, rejected options, raw logs.}}

</details>

</section>

<!-- Next chapter: a new <section class="acc-blue|acc-purple|acc-orange">, chapter-no 02, a different figure kind and device. -->

## What we're not sure about

- {{Each caveat on its own line, with what it would change if it is wrong.}}

## What's next

{{The recommendation in one or two sentences.}}

**Next step:** {{action}} · **Owner:** {{name, or "not yet set"}} · **By:** {{YYYY-MM-DD, or "not yet set"}}

## Appendix

<details class="evidence" markdown="1">
<summary><span class="kick">The receipts</span> Every number in one place</summary>

| Number | What it measures | Compared with | Source |
|---|---|---|---|
| {{value}} | {{meaning}} | {{baseline}} | {{path or link}} |

</details>

<details class="evidence" markdown="1">
<summary><span class="kick">Words</span> Glossary: every term in one place, in plain words</summary>

<dl class="words">
<dt>{{Term}}</dt><dd>{{Precise one-line meaning.}} {{Everyday analogy, if one fits.}}</dd>
</dl>

</details>

<details class="evidence" markdown="1">
<summary><span class="kick">Rewind</span> Changelog: what changed, and when</summary>

- {{YYYY-MM-DD}}: {{what changed, one line}}.

</details>
