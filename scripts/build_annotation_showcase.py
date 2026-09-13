"""Render real, cached training annotations into an offline gallery and GitHub pages.

No API calls. Fixed editorial selection illustrates different observed transitions;
it is not a random quality sample or an evaluation of trained-model predictions.
"""
import argparse
import base64
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
from datetime import datetime

from open_relief.annotation import validate_annotation
from open_relief.adapter import format_training
from open_relief.dataset import load_examples, digest_file

CASES = [
    ("3cbb32921fe1afe089e3977f", "harad", "Deterioration", "Trade, prices and conflict before an observed phase increase"),
    ("0029fa7cda0aa0fd84bee13c", "beni", "Persistent crisis", "Elevated staple prices and conflict alongside a stable IPC phase"),
    ("002484ea2c5aaa22f62d46e8", "oubritenga", "Improvement", "An improving outcome despite mixed contextual pressures"),
]
CHANNELS = [
    ("fcs_rt mean", "FCS normalized index", "#cccccc"),
    ("rcsi_rt mean", "rCSI normalized index", "#cccccc"),
    ("portwatch_import_cargo", "Cargo imports", "#cccccc"),
    ("wfp_staple_price", "Staple price", "#cccccc"),
    ("acled_events", "Conflict events", "#cccccc"),
    ("chirps_rainfall", "Rainfall", "#cccccc"),
]


def esc(value):
    return html.escape(str(value), quote=True)


def month(value):
    return datetime.fromisoformat(value[:7] + "-01")


def plot_case(example, title, output):
    sample, target = example["input"], example["target"]
    geo = sample["geography"]
    channels = {c["name"]: c for c in sample["channels"]}
    fonts = Path(__file__).resolve().parents[1] / 'docs/examples/fonts'
    body = font_manager.FontProperties(fname=str(fonts / 'DMSans-Regular.ttf'))
    heading = font_manager.FontProperties(fname=str(fonts / 'Manrope-Medium.ttf'))
    font_manager.fontManager.addfont(str(fonts / 'DMSans-Regular.ttf'))
    bg, panel, fg, muted = "#0b0b0b", "#202020", "#e5e5e5", "#aaaaaa"
    accent = "#ee8277" if target['phase_change'] > 0 else "#b5d6b7" if target['phase_change'] < 0 else "#efb775"
    with plt.rc_context({"font.family": body.get_name(), "font.size": 10,
                         "text.color": fg, "axes.labelcolor": muted,
                         "xtick.color": muted, "ytick.color": muted,
                         "axes.edgecolor": "#383838", "savefig.facecolor": bg}):
        fig = plt.figure(figsize=(15, 11), facecolor=bg)
        grid = fig.add_gridspec(4, 2, height_ratios=[.65, 1, 1, 1],
                               left=.075, right=.96, bottom=.09, top=.82,
                               hspace=.92, wspace=.27)
        fig.text(.075, .956, "OPENRELIEF  /  ANNOTATION ATLAS", color=muted, size=10)
        fig.text(.075, .912, f"{geo['admin2']} · {geo['country']}", size=25, fontproperties=heading)
        fig.text(.075, .875, title, size=13, color=muted)
        timeline = fig.add_subplot(grid[0, :], facecolor=panel)
        first = month(sample["channels"][0]["months"][0])
        cutoff = datetime.fromisoformat(sample["cutoff"].replace("Z", "+00:00")).replace(tzinfo=None)
        future = month(target["target_month"])
        last = sample["last_available_phase"]
        known = month(last["event_month"])
        timeline.axvspan(first, cutoff, color="#cccccc", alpha=.025)
        timeline.axvspan(cutoff, future, color=accent, alpha=.045)
        timeline.plot([first, future], [.35, .35], color="#555555", lw=1)
        timeline.scatter([known, cutoff, future], [.35]*3,
                         c=["#cccccc", "#cccccc", accent], s=35, zorder=4)
        timeline.annotate(f"Known assessment · IPC {last['phase']}\n{last['event_month']}",
                          (known, .35), xytext=(-6, 13), textcoords="offset points", ha="right", size=9)
        timeline.annotate(f"Cutoff\n{sample['cutoff'][:10]}", (cutoff, .35),
                          xytext=(6, -12), textcoords="offset points", size=9, va="top")
        timeline.annotate(f"Observed target · IPC {target['phase']}\n{target['target_month']}",
                          (future, .35), xytext=(-4, 13), textcoords="offset points", ha="right", size=9, color=accent)
        timeline.set_ylim(-.3, 1.2)
        timeline.set_xticks([]); timeline.set_yticks([])
        timeline.margins(x=.035)
        for spine in timeline.spines.values():
            spine.set_visible(False)
        for index, (name, label, color) in enumerate(CHANNELS):
            c = channels[name]
            ax = fig.add_subplot(grid[1 + index//2, index % 2], facecolor='none')
            pos = ax.get_position()
            card = FancyBboxPatch((pos.x0-.017, pos.y0-.025), pos.width+.029, pos.height+.075,
                                 boxstyle='round,pad=0.006,rounding_size=0.012',
                                 facecolor='#191919', edgecolor='#333333', linewidth=.6,
                                 transform=fig.transFigure, zorder=-1)
            fig.patches.append(card)
            dates = [month(m) for m in c["months"]]
            values = [float("nan") if v is None else v for v in c["values"]]
            ax.plot(dates, values, color=color, marker="o", markersize=3.5, lw=1.3)
            ax.set_title(label, loc="left", fontsize=12, fontproperties=heading, color=fg, pad=24)
            unit = "Normalized index; direction unknown" if name.startswith(("fcs", "rcsi")) else c["unit"]
            ax.text(0, 1.07, f"{c['geography_level']} · {unit}", transform=ax.transAxes, color=muted, size=8)
            observed = [(d, v) for d, v in zip(dates, c["values"]) if v is not None]
            if observed:
                final = observed[-1][1]
                label_value = f"{final/1e6:.3g}M" if abs(final)>=1e6 else f"{final/1e3:.3g}k" if abs(final)>=1e3 else f"{final:.3g}"
                ax.annotate(label_value, observed[-1], xytext=(-5, 8),
                            textcoords="offset points", ha="right", color=color, size=9)
            else:
                ax.text(.5, .5, "No available observations", transform=ax.transAxes,
                        ha="center", color=muted)
            missing = sum(v is None for v in c["values"])
            if missing:
                ax.text(.02, .08, f"{missing}/6 months unavailable", transform=ax.transAxes, color=muted, size=8)
            ax.set_xlim(dates[0], dates[-1]); ax.margins(y=.3)
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e6:g}M" if abs(v)>=1e6 else f"{v/1e3:g}k" if abs(v)>=1e3 else f"{v:g}"))
            ax.grid(axis="y", color="#ffffff", alpha=.07, linewidth=.6)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=8)
        fig.text(.075, .038, "RETROSPECTIVE TRAINING EXAMPLE · Future target supplied to the annotation teacher; not a model forecast.", size=10, color=muted)
        fig.text(.075, .018, "Original units · gaps remain missing · national covariates do not establish district exposure or causation.", size=9, color=muted)
        fig.savefig(output, dpi=130, metadata={"Software": "OpenRelief annotation showcase"})
        plt.close(fig)


def tags(channels):
    return '<div class="tags">' + ''.join(f'<code>{esc(c)}</code>' for c in channels) + '</div>'


def render_pipeline():
    """Code-native diagram matching the frontend methodology cards and wires."""
    fonts = Path(__file__).resolve().parents[1] / 'docs/examples/fonts'
    face = base64.b64encode((fonts / 'Manrope-Medium.ttf').read_bytes()).decode()
    body = base64.b64encode((fonts / 'DMSans-Regular.ttf').read_bytes()).decode()
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="680" viewBox="0 0 1360 680" role="img" aria-labelledby="title desc">
    <title id="title">OpenRelief structured annotation pipeline</title>
    <desc id="desc">Historical inputs and an observed future label enter a structured teacher request. Cached evidence, hypotheses and actions become training supervision, not inference inputs.</desc>
    <defs><style>@font-face{{font-family:Manrope;src:url(data:font/ttf;base64,{face})}}@font-face{{font-family:DM;src:url(data:font/ttf;base64,{body})}}
    text{{font-family:DM,sans-serif;fill:#ddd;font-size:15px}}.heading{{font-family:Manrope,sans-serif;font-size:32px}}.label{{font-size:11px;letter-spacing:1.8px;fill:#999}}.small{{font-size:12px;fill:#999}}.node{{fill:#202020;stroke:#fff;stroke-opacity:.12}}.wire{{fill:none;stroke:#aaa;stroke-opacity:.3;stroke-width:1}}.dot{{fill:#bbb}}</style>
    <radialGradient id="bg"><stop stop-color="#242424"/><stop offset="1" stop-color="#0b0b0b"/></radialGradient>
    <linearGradient id="glass"><stop stop-color="#343434"/><stop offset="1" stop-color="#1b1b1b"/></linearGradient></defs>
    <rect width="1360" height="680" rx="18" fill="url(#bg)"/>
    <text x="60" y="48" class="label">OPENRELIEF / ANNOTATION PIPELINE</text>
    <text x="60" y="98" class="heading">How the training explanation takes shape.</text>
    <text x="60" y="151" class="label">01  OBSERVE THE SIGNALS</text>
    <text x="552" y="151" class="label">02  CONNECT THE EVIDENCE</text>
    <text x="990" y="151" class="label">03  STRUCTURE THE SUPERVISION</text>''']
    for i, (label, subtitle) in enumerate([
        ('Food-security history', 'HFID / district indices and IPC chronology'),
        ('Shipping and prices', 'PortWatch + WFP / national context'),
        ('Conflict and rainfall', 'ACLED + CHIRPS / national context'),
        ('Availability and provenance', '21 channels / six months / source hashes'),
        ('Observed future IPC phase', 'Supplied to the teacher in training only'),
    ]):
        y = 180 + i*76
        parts.append(f'<path class="wire" d="M380 {y+29} C445 {y+29},465 352,520 352"/><rect class="node" x="60" y="{y}" width="320" height="60" rx="12"/><circle cx="82" cy="{y+29}" r="3" class="dot"/><text x="98" y="{y+25}">{esc(label)}</text><text x="98" y="{y+44}" class="small">{esc(subtitle)}</text><circle cx="380" cy="{y+29}" r="2.5" class="dot"/>')
    for y in [253, 352, 451]:
        parts.append(f'<path class="wire" d="M840 352 C900 352,930 {y},990 {y}"/>')
    parts.append('''<rect x="520" y="217" width="320" height="270" rx="19" fill="url(#glass)" stroke="#fff" stroke-opacity=".18"/>
      <circle cx="680" cy="270" r="25" fill="none" stroke="#777" stroke-width=".8"/>
      <circle cx="680" cy="270" r="33" fill="none" stroke="#555" stroke-width=".6"/>
      <path d="M665 270h30m-15-15v30" stroke="#bbb" stroke-width="1"/>
      <text x="680" y="328" text-anchor="middle" class="label">STRUCTURED LLM TEACHER</text>
      <text x="680" y="365" text-anchor="middle" style="font-family:Manrope;font-size:26px">Connect the dots.</text>
      <path d="M553 386h254" stroke="#fff" stroke-opacity=".1"/>
      <text x="680" y="413" text-anchor="middle" class="small">Preserve the label · reference the channels</text>
      <text x="680" y="436" text-anchor="middle" class="small">Separate observations from hypotheses</text>
      <text x="680" y="463" text-anchor="middle" class="small">Strict JSON · validation · request cache</text>''')
    for y, label, subtitle in [
        (213, 'Evidence claims', 'Observed patterns + channel references'),
        (312, 'Interaction hypotheses', 'Proposed mechanisms + uncertainty'),
        (411, 'Rationale and actions', 'Driver citations + phase-aligned urgency'),
    ]:
        parts.append(f'<rect class="node" x="990" y="{y}" width="310" height="80" rx="12"/><circle cx="990" cy="{y+40}" r="2.5" class="dot"/><text x="1012" y="{y+31}">{label}</text><text x="1012" y="{y+55}" class="small">{subtitle}</text>')
    parts.append('''<path d="M60 573h1240" stroke="#fff" stroke-opacity=".1"/>
      <text x="60" y="605" class="label">TRAINING ANSWER</text>
      <text x="260" y="605">IPC phase + generated rationale + proposed action strings → OpenTSLM fine-tuning</text>
      <text x="60" y="645" class="small">Retrospective teacher supervision · future labels and annotations are excluded from inference inputs · hypotheses are not proven causes.</text></svg>''')
    return ''.join(parts)


def render_case(case):
    s, t, a = case["input"], case["target"], case["annotation"]
    g = s["geography"]
    precursors = ''.join(
        f'<article class="claim"><span class="kind">{esc(c["provenance"])}</span><p>{esc(c["statement"])}</p>'
        f'{tags(c["channels"])}<p class="small">{esc(c["uncertainty"])}</p></article>'
        for c in a["precursor_patterns"])
    hypotheses = ''.join(
        f'<article class="claim hypothesis"><span class="kind">Hypothesis · {esc(c["provenance"])}</span>'
        f'<p>{esc(c["statement"])}</p><h4>Proposed mechanism</h4><p>{esc(c["mechanism"])}</p>'
        f'{tags(c["channels"])}<p class="small">{esc(c["uncertainty"])}</p></article>'
        for c in a["interaction_hypotheses"])
    actions = ''.join(
        f'<article class="claim action"><span class="kind">{esc(c["urgency"].replace("_", " "))}</span>'
        f'<p>{esc(c["action"])}</p>{tags(c["driver_channels"])}<p class="small">{esc(c["justification"])}</p></article>'
        for c in a["recommended_actions"])
    return f'''<section class="case" id="{case['slug']}">
      <div class="eyebrow">{esc(case['transition'])} / {esc(g['iso3'])}</div>
      <h2>{esc(g['admin2'])}<span>{esc(g['country'])}</span></h2>
      <p class="lede">{esc(case['title'])}</p>
      <div class="facts"><div><b>{esc(s['cutoff'][:10])}</b><span>Forecast cutoff</span></div>
      <div><b>IPC {s['last_available_phase']['phase']} → {t['phase']}</b><span>Known assessment → observed target</span></div>
      <div><b>{esc(t['target_month'])}</b><span>Observed target month · training label</span></div></div>
      <img src="{case['slug']}.png" alt="Six historical input charts and an assessment timeline for {esc(g['admin2'])}" width="1950" height="1430" loading="lazy">
      <div class="step"><span>01</span><div><h3>Read the observed signals</h3><p>Teacher claims with their original provenance labels and channel references.</p></div></div>
      <details><summary>Inspect {len(a['precursor_patterns'])} precursor claims</summary><div class="claims">{precursors}</div></details>
      <div class="step"><span>02</span><div><h3>Connect signals across domains</h3><p>Generated hypotheses, with mechanisms and explicit uncertainty.</p></div></div>
      <div class="claims">{hypotheses}</div>
      <div class="step"><span>03</span><div><h3>Build the training explanation</h3><p>Verbatim rationale returned by the annotation endpoint.</p></div></div>
      <blockquote>{esc(a['rationale'])}</blockquote>
      <div class="step"><span>04</span><div><h3>Ground proposed actions in the drivers</h3><p>Retrospective supervision tied to the supplied target phase, not operational guidance.</p></div></div>
      <div class="claims">{actions}</div>
      <aside><b>Teacher uncertainty</b><p>{esc(a['uncertainty'])}</p><p>Annotation-quality confidence: {a['confidence']:.2f}. This is not a forecast probability.</p></aside>
      <details><summary>Trace this example to its cached response</summary>
      <p>Training-partition sample <code>{esc(s['sample_id'])}</code>. Teacher <code>{esc(case['teacher']['model'])}</code>.</p>
      <p>Request SHA-256 <code>{esc(case['teacher']['request_sha256'])}</code>.</p>
      <p>Dataset version <code>{esc(s['dataset_version'])}</code>.</p>
      <p><a href="examples.json">Download the exact inputs, targets, annotations and serialized training answers</a>.</p></details>
    </section>'''


def render_markdown(cases):
    text = """# Annotation atlas

Real time-series inputs and cached LLM-generated training annotations, rendered without new API calls.

![Structured annotation workflow](pipeline.svg)
Open [index.html](index.html) locally for the interactive gallery, or read the examples below on GitHub.

These three **training-partition** examples were selected editorially to illustrate deterioration,
persistent crisis and improvement across three countries. They are not a random quality sample,
held-out predictions, or evidence of model accuracy. The teacher was given each observed future
phase. Its language is preserved verbatim; hypotheses are not established causes.

The pipeline couples objective labels to signal descriptions, cross-domain hypotheses, a rationale,
driver-cited actions and uncertainty. Training retains the phase, rationale and action strings;
the richer provenance remains in the annotation artifact. Confidence describes annotation quality,
not forecast probability. [Exact example data](examples.json) · [Build manifest](manifest.json).

"""
    for case in cases:
        s, t, a = case['input'], case['target'], case['annotation']
        text += f"## {s['geography']['admin2']}, {s['geography']['country']} — {case['transition']}\n\n"
        text += f"Cutoff **{s['cutoff'][:10]}** · known IPC **{s['last_available_phase']['phase']}** → observed target **{t['phase']}** in **{t['target_month']}**.\n\n"
        text += f"![Historical signals for {s['geography']['admin2']}]({case['slug']}.png)\n\n"
        text += f"**Generated rationale**\n\n> {a['rationale']}\n\n"
        text += "<details>\n<summary>Cross-domain hypotheses and proposed actions — verbatim teacher output</summary>\n\n"
        for c in a['interaction_hypotheses']:
            text += f"**Hypothesis ({c['provenance']})**\n\n{c['statement']}\n\n{c['mechanism']}\n\n"
            text += 'Channels: ' + ', '.join(f'`{n}`' for n in c['channels']) + f".\n\nUncertainty: {c['uncertainty']}\n\n"
        for c in a['recommended_actions']:
            text += f"**Proposed action · {c['urgency']}**\n\n{c['action']}\n\n{c['justification']}\n\n"
            text += 'Drivers: ' + ', '.join(f'`{n}`' for n in c['driver_channels']) + '.\n\n'
        text += f"</details>\n\nSample `{s['sample_id']}` · cached teacher `{case['teacher']['model']}`.\n\n"
    text += "## Rebuild\n\n```sh\n.venv/bin/python scripts/build_annotation_showcase.py\n```\n\n"
    text += "Requires the prepared dataset and existing training annotation file; no network access is used. "
    text += "Plots show six original channels out of 21, with original units and missing values preserved. "
    text += "The JSON contains all 21 channels, availability times and source hashes. "
    text += "Source attribution and reuse limitations are in [the dataset card](../../DATASET_CARD.md).\n"
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('artifacts/multimodal'))
    parser.add_argument('--annotations', type=Path, default=Path('artifacts/annotations-training.jsonl'))
    parser.add_argument('--output', type=Path, default=Path('docs/examples/annotation-atlas'))
    args = parser.parse_args()
    examples = {e['input']['sample_id']: e for e in load_examples(args.dataset, 'train')}
    annotations = {}
    for row in map(json.loads, args.annotations.read_text().splitlines()):
        if row['sample_id'] in annotations:
            raise ValueError('Duplicate annotation ID')
        annotations[row['sample_id']] = row
    selected = []
    for sid, slug, transition, title in CASES:
        example, row = examples[sid], annotations[sid]
        validate_annotation(row['annotation'], example)
        answer = format_training(example, '', row)['answer']
        selected.append({**example, 'slug': slug, 'transition': transition, 'title': title,
                         'annotation': row['annotation'], 'training_answer': json.loads(answer),
                         'teacher': {'model': row['model'], 'request_sha256': row['request_sha256']}})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'pipeline.svg').write_text(render_pipeline())
    for case in selected:
        plot_case(case, case['title'], args.output / f"{case['slug']}.png")
    (args.output / 'examples.json').write_text(json.dumps(selected, indent=2, ensure_ascii=False) + '\n')
    template = (Path(__file__).parent / 'annotation_showcase.html').read_text()
    (args.output / 'index.html').write_text(template.replace('<!-- CASES -->', ''.join(map(render_case, selected))))
    (args.output / 'README.md').write_text(render_markdown(selected))
    manifest = {'dataset_version': selected[0]['input']['dataset_version'],
                'annotation_file_sha256': digest_file(args.annotations),
                'sample_ids': [c['input']['sample_id'] for c in selected],
                'selection': 'Editorial training examples: deterioration, stable crisis and improvement; not a quality or performance sample.',
                'network_calls': 0,
                'files': {p.name: digest_file(p) for p in sorted(args.output.iterdir()) if p.is_file() and p.name != 'manifest.json'}}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'cases': len(selected), 'output': str(args.output), 'network_calls': 0}))


if __name__ == '__main__':
    main()
