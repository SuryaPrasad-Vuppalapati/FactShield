import os
import gradio as gr
import pandas as pd
from datasets import load_dataset
from huggingface_hub import login
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("HF_TOKEN", "")
if token:
 login(token=token)

APP_HEAD_JS = """
<script>
(function () {
  if (window.__factshieldBound) return;
  window.__factshieldBound = true;

  function byId(id) { return document.getElementById(id); }

  function renderDetail(d, key) {
    var panel = byId('detail-panel');
    if (!panel) return;
    var iconEl = byId('detail-icon');
    var nameEl = byId('detail-name');
    var phaseEl = byId('detail-phase');
    var descEl = byId('detail-desc');
    var tagsEl = byId('detail-tags');
    var headerEl = byId('detail-header');

    if (iconEl) {
      var letter = (d && d.name ? d.name : key || '?').charAt(0).toUpperCase();
      iconEl.textContent = letter;
      iconEl.style.background = (d && d.bg) || '#f1f5f9';
      iconEl.style.color = (d && d.color) || '#334155';
      iconEl.style.fontWeight = '700';
      iconEl.style.fontSize = '13px';
    }
    if (nameEl) nameEl.textContent = (d && d.name) || key || 'Details';
    if (phaseEl) phaseEl.textContent = (d && d.phase) || 'Pipeline component';
    if (descEl) {
      descEl.textContent = (d && d.desc) || 'No description available.';
      descEl.style.textAlign = 'justify';
    }
    if (headerEl) headerEl.style.background = (d && d.bg) || '#ffffff';
    if (tagsEl) {
      var tags = (d && d.tags) || [key || 'item'];
      tagsEl.innerHTML = tags.map(function (t) {
        return '<span class="detail-tag">' + t + '</span>';
      }).join('');
    }

    panel.classList.add('visible');
    setTimeout(function () {
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }

  window.showDetail = function (key) {
    var panel = byId('detail-panel');
    if (!panel) return;

    if (window.active === key && panel.classList.contains('visible')) {
      panel.classList.remove('visible');
      window.active = null;
      return;
    }
    window.active = key;

    if (window.D && window.D[key]) {
      renderDetail(window.D[key], key);
      return;
    }

    var node = document.querySelector('[data-key="' + key + '"]');
    if (!node) return;
    var title = node.querySelector('.node-title, .hub-text');
    var sub = node.querySelector('.node-sub, .hub-sub');
    renderDetail({
      name: title ? title.textContent.trim() : key,
      phase: 'Pipeline component',
      desc: sub ? sub.textContent.trim() : 'Details unavailable.',
      tags: [key],
      bg: '#f8fafc',
      color: '#334155'
    }, key);
  };

  window.showPhaseInfo = function (phase) {
    if (!window.phaseInfo || !window.phaseInfo[phase]) return;
    var info = window.phaseInfo[phase];
    renderDetail({
      name: info.title,
      phase: 'Click any node card for more details',
      desc: info.text,
      tags: info.tags || [phase],
      bg: info.color,
      color: info.border
    }, 'phase-' + phase);
  };

  window.setPhase = function (phase) {
    var allBtn = byId('all-btn');
    if (allBtn) allBtn.classList.toggle('active', phase === 'all');
    ['1', '2', '3', '4'].forEach(function (n, i) {
      var step = byId('ts' + n);
      if (!step) return;
      step.classList.remove('active', 'done');
      if (phase !== 'all') {
        var idx = parseInt(String(phase).replace('p', ''), 10);
        if (i + 1 < idx) step.classList.add('done');
        else if (i + 1 === idx) step.classList.add('active');
      }
    });

    var phaseTrackPct = { p1: '0%', p2: '33%', p3: '66%', p4: '100%' };
    var fill = byId('tl-fill');
    if (fill) fill.style.width = phase === 'all' ? '0%' : (phaseTrackPct[phase] || '0%');

    ['p1', 'p2', 'p3', 'p4'].forEach(function (p) {
      var el = byId('pg-' + p);
      if (el) el.classList.toggle('dimmed', phase !== 'all' && phase !== p);
    });

    var panel = byId('detail-panel');
    if (panel) panel.classList.remove('visible');
    window.active = null;
    if (phase !== 'all') window.showPhaseInfo(phase);
  };

  window.showDoc = function (id, btn) {
    document.querySelectorAll('.doc-panel').forEach(function (p) { p.classList.remove('visible'); });
    document.querySelectorAll('.docs-nav button').forEach(function (b) { b.classList.remove('active'); });
    var panel = byId('doc-' + id);
    if (panel) panel.classList.add('visible');
    if (btn) btn.classList.add('active');
  };

  window.showModel = function (name) {
    document.querySelectorAll('.model-btn').forEach(function (b) { b.classList.remove('active'); });
    document.querySelectorAll('.model-panel').forEach(function (p) { p.style.display = 'none'; });
    var btn = byId('btn-' + name);
    var panel = byId('panel-' + name);
    if (btn) btn.classList.add('active');
    if (panel) panel.style.display = 'block';
  };

  window.filterRes = function (type, btn) {
    document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.result-item').forEach(function (item) {
      var m = item.getAttribute('data-method') || '';
      var show = type === 'all' ||
        (type === 'selfcheck' && m.indexOf('selfcheck') !== -1) ||
        (type === 'entailment' && m === 'minicheck') ||
        (type === 'tokprob' && m === 'token_prob_classifier');
      var visibleDisplay = item.tagName === 'TR' ? 'table-row' : 'block';
      item.style.display = show ? visibleDisplay : 'none';
    });
  };

  window.resultsInit = function () {
    var els = document.querySelectorAll('[data-width]');
    if (!els.length) {
      setTimeout(window.resultsInit, 200);
      return;
    }
    els.forEach(function (el) {
      setTimeout(function () {
        el.style.width = el.getAttribute('data-width');
      }, 400);
    });
  };

  function bindClicks() {
    var allBtn = byId('all-btn');
    if (allBtn && !allBtn.dataset.bound) {
      allBtn.dataset.bound = '1';
      allBtn.addEventListener('click', function () { window.setPhase('all'); });
    }
    ['1', '2', '3', '4'].forEach(function (n) {
      var step = byId('ts' + n);
      if (step && !step.dataset.bound) {
        step.dataset.bound = '1';
        step.addEventListener('click', function () { window.setPhase('p' + n); });
      }
    });
    document.querySelectorAll('[data-key]').forEach(function (el) {
      if (el.dataset.bound) return;
      el.dataset.bound = '1';
      el.style.cursor = 'pointer';
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        window.showDetail(el.getAttribute('data-key'));
      });
    });
  }

  function boot() {
    bindClicks();
    window.resultsInit();
    if (document.querySelector('.model-btn') && !document.querySelector('.model-btn.active')) {
      window.showModel('bart');
    }
  }

  document.addEventListener('DOMContentLoaded', boot);
  setTimeout(boot, 100);
  setTimeout(boot, 500);
})();
</script>
"""

ARCHITECTURE_HTML = """
<script>
function fsInit() {
 var allBtn = document.getElementById('all-btn');
 if (!allBtn) { setTimeout(fsInit, 100); return; }

 allBtn.addEventListener('click', function() { setPhase('all'); });

 ['1','2','3','4'].forEach(function(n) {
 var step = document.getElementById('ts'+n);
 if (step) {
 step.style.cursor = 'pointer';
 step.addEventListener('click', function() { setPhase('p'+n); });
 }
 });

 document.querySelectorAll('[data-key]').forEach(function(el) {
 el.style.cursor = 'pointer';
 el.addEventListener('click', function(e) {
 e.stopPropagation();
 showDetail(el.getAttribute('data-key'));
 });
 });
}
fsInit();

var phaseInfo = {
 'p1': {
 title: 'Phase 1 - Data Ingestion',

 color: '#ecfdf5',
 border: '#10b981',
 text: 'Downloads CNN/DailyMail, XSum, and FaithBench datasets. Creates 70/15/15 train/val/test splits with seed=42 for reproducibility. Builds binary hallucination labels from FaithBench annotations. Pushes all splits and labels to HuggingFace Hub.',
 tags: ['data_loader.py', 'splitter.py', 'faithbench_labels.py', '1400 CNN/DM docs', '1400 XSum docs', '560 FaithBench docs']
 },
 'p2': {
 title: 'Phase 2 - Cache Generation',

 color: '#ede9fe',
 border: '#7c3aed',
 text: 'Runs on Kaggle T4 GPU. Generates three output types per model×dataset combo: beam-search summaries (num_beams=4), K=10 stochastic samples (temperature=1.0), and token log-probabilities (greedy, output_scores=True). Uses batch_size=16, float16, and torch.compile for 8-10x speedup.',
 tags: ['generate.py', 'BART, T5, PEGASUS', 'batch_size=16', 'float16', 'torch.compile', '27 configs total']
 },
 'p3': {
 title: 'Phase 3 - Scoring Pipelines',

 color: '#fff7ed',
 border: '#ea580c',
 text: 'Three parallel pipelines run locally. SelfCheckGPT scores sentence consistency across K=10 samples using BERTScore, NLI (DeBERTa), and Ngram. Entailment pipeline checks each sentence against its source using MiniCheck. Token probability pipeline extracts 5 uncertainty features and trains a logistic regression classifier.',
 tags: ['selfcheck/pipeline.py', 'entailment/pipeline.py', 'token_prob/pipeline.py', '30,237 task1 rows', '10,080 task2 rows', '10,080 task3 rows']
 },
 'p4': {
 title: 'Phase 4 - Evaluation',

 color: '#f0fdf4',
 border: '#16a34a',
 text: 'Loads all results from HuggingFace Hub. Filters to FaithBench (the only dataset with hallucination labels). Aggregates sentence-level scores to doc-level via mean. Splits 50/50 val/test with no data leakage. Computes AUROC, AUPRC, F1 (threshold tuned on val), and ECE. Best result: PEGASUS + SelfCheck NLI = AUROC 0.5653.',
 tags: ['evaluate.py', 'assemble_final_table.py', 'validate_all.py', 'AUROC, AUPRC, F1, ECE', 'FaithBench only', '36/36 validation passed']
 }
};

var D = {
 'data-loader':{ icon:'', phase:'Phase 1 - Data ingestion', bg:'#ecfdf5', color:'#065f46',
 name:'data_loader.py',
 desc:'Downloads CNN/DailyMail (3.0.0), XSum (EdinburghNLP/xsum), and FaithBench CSV directly from GitHub. Saves raw data to data/raw/ locally. Run once before splitting.',
 tags:['cnn_dailymail 3.0.0','EdinburghNLP/xsum','FaithBench.csv','data/raw/'] },
 'splitter':{ icon:'', phase:'Phase 1 - Data ingestion', bg:'#ecfdf5', color:'#065f46',
 name:'splitter.py',
 desc:'Creates reproducible 70/15/15 train/val/test splits using seed=42. 1400 train docs for CNN/DM and XSum, 560 for FaithBench. Pushes all 3 splits to factshield-team/cache on HuggingFace Hub.',
 tags:['seed=42','1400 cnndm/xsum','560 faithbench','push_to_hub'] },
 'labels':{ icon:'', phase:'Phase 1 - Data ingestion', bg:'#ecfdf5', color:'#065f46',
 name:'build_faithbench_labels.py',
 desc:'Maps FaithBench worst-label and best-label annotations to binary values. Unwanted/Questionable → 1 (hallucinated), otherwise → 0. Pushes 800 labeled rows to faithbench-labels repo.',
 tags:['label_binary_worst','label_binary_best','800 rows','Unwanted=1'] },
 'hf-splits':{ icon:'', phase:'HuggingFace Hub', bg:'#f5f3ff', color:'#6d28d9',
 name:'factshield-team/cache + faithbench-labels',
 desc:'Central Hub storage for all splits. Every team member loads from here - no local data dependency needed. cnndm_splits, xsum_splits, faithbench_splits configs are all available.',
 tags:['cnndm_splits','xsum_splits','faithbench_splits','private=True'] },
 'generate':{ icon:'', phase:'Phase 2 - Cache generation (Kaggle T4)', bg:'#ede9fe', color:'#4c1d95',
 name:'generate.py',
 desc:'Three generation functions on Kaggle T4 GPU: generate_summaries() uses beam search (num_beams=4), generate_k_samples() uses temperature sampling (K=10, temp=1.0), generate_with_scores() uses greedy decoding with output_scores=True. Batched inference with float16 and torch.compile for 8-10x speedup.',
 tags:['batch_size=16','float16','torch.compile','num_beams=4','K=10','output_scores=True'] },
 'hf-cache':{ icon:'', phase:'HuggingFace Hub', bg:'#f5f3ff', color:'#6d28d9',
 name:'factshield-team/cache - 27 configs',
 desc:'3 models (BART, T5, PEGASUS) × 3 datasets (CNN/DM, XSum, FaithBench) × 3 output types (summaries, k_samples, token_scores). All generated on Kaggle T4 GPU and pushed to HuggingFace Hub.',
 tags:['bart_cnndm_summaries','t5_xsum_k_samples','pegasus_faithbench_token_scores','... 27 total'] },
 'selfcheck':{ icon:'', phase:'Phase 3 - Pipeline 1', bg:'#fff7ed', color:'#7c2d12',
 name:'SelfCheckGPT pipeline',
 desc:'Loads K=10 stochastic samples from cache. Scores each sentence in the primary summary for consistency across samples. Three modes: BERTScore (semantic similarity), NLI via cross-encoder/nli-deberta-v3-large (entailment), Ngram (unigram overlap). Best result: PEGASUS + NLI = AUROC 0.5653.',
 tags:['30,237 rows','bert, nli, ngram','K=10','AUROC 0.5653 (pegasus/nli)'] },
 'entailment':{ icon:'', phase:'Phase 3 - Pipeline 2', bg:'#eff6ff', color:'#1e3a8a',
 name:'Entailment verification pipeline',
 desc:'Loads beam-search summaries. Scores each sentence against its source document using MiniCheck (roberta-large fine-tuned for factual consistency). Score ~1 = grounded in source, ~0 = hallucinated. Best: PEGASUS + MiniCheck = AUROC 0.5220.',
 tags:['10,080 rows','MiniCheck','roberta-large','AUROC 0.5220 (pegasus)'] },
 'tokprob':{ icon:'', phase:'Phase 3 - Pipeline 3', bg:'#fffbeb', color:'#78350f',
 name:'Token probability pipeline',
 desc:'Decodes stored token log-probs to float32. Extracts 5 features: perplexity, mean entropy, max entropy, tail mean NLL (last 5 tokens), sentence length. Trains logistic regression with cross-validation on FaithBench labels. Best: T5 = AUROC 0.5486.',
 tags:['10,080 rows','5 features','LogisticRegression','AUROC 0.5486 (t5)'] },
 'hf-results':{ icon:'', phase:'HuggingFace Hub', bg:'#f5f3ff', color:'#6d28d9',
 name:'factshield-team/results',
 desc:'task1_scores: 30,237 rows. task2_scores: 10,080 rows. task3_scores: 10,080 rows. Each row is a doc-level score with method, summarizer, dataset, and score columns.',
 tags:['task1_scores','task2_scores','task3_scores','final_table'] },
 'evaluate':{ icon:'', phase:'Phase 4 - Evaluation', bg:'#f0fdf4', color:'#14532d',
 name:'evaluate.py (per pipeline)',
 desc:'Loads results from Hub, filters to FaithBench only (the only labeled dataset), aggregates sentence-level scores to doc-level via mean, splits 50/50 val/test with no leakage, computes AUROC, AUPRC, F1 with threshold tuned on val, and ECE.',
 tags:['AUROC','AUPRC','F1','ECE','FaithBench only','50/50 val/test'] },
 'final-table':{ icon:'', phase:'Phase 5 - Final results', bg:'#f0fdf4', color:'#14532d',
 name:'assemble_final_table.py',
 desc:'Loads all 3 task results, normalizes method names, merges with FaithBench labels, computes AUROC and AUPRC per (method, summarizer, dataset) combo. Sorts descending by AUROC and pushes final_table to Hub.',
 tags:['15 rows','sorted by AUROC','final_table config','push_to_hub'] },
 'validate':{ icon:'', phase:'Phase 6 - CI / Validation', bg:'#f0fdf4', color:'#14532d',
 name:'validate_all.py - 36/36 passed',
 desc:'Checks all 27 cache configs, 3 splits, faithbench labels, 4 result configs, and task3 classifier are present and non-empty on HuggingFace Hub. Runs in GitHub Actions CI. 36/36 checks passed.',
 tags:['27 cache configs','3 splits','4 result configs','36/36 passed','GitHub Actions'] }
};

var active = null;

function showDetail(key) {
 var d = D[key];
 if (!d) return;
 var panel = document.getElementById('detail-panel');
 if (!panel) return;
 if (active === key && panel.classList.contains('visible')) {
 panel.classList.remove('visible');
 active = null;
 return;
 }
 active = key;
 var iconEl = document.getElementById('detail-icon');
 var nameEl = document.getElementById('detail-name');
 var phaseEl = document.getElementById('detail-phase');
 var descEl = document.getElementById('detail-desc');
 var tagsEl = document.getElementById('detail-tags');
 var headerEl = document.getElementById('detail-header');
 if (iconEl) { iconEl.textContent = d.name ? d.name.charAt(0).toUpperCase() : '?'; iconEl.style.background = d.bg; iconEl.style.color = d.color; iconEl.style.fontWeight = '700'; iconEl.style.fontSize = '13px'; }
 if (nameEl) nameEl.textContent = d.name;
 if (phaseEl) phaseEl.textContent = d.phase;
 if (descEl) { descEl.textContent = d.desc; descEl.style.textAlign = 'justify'; }
 if (headerEl) headerEl.style.background = d.bg;
 if (tagsEl) tagsEl.innerHTML = d.tags.map(function(t) {
 return '<span class="detail-tag">' + t + '</span>';
 }).join('');
 panel.classList.add('visible');
 setTimeout(function() {
 panel.scrollIntoView({behavior:'smooth', block:'nearest'});
 }, 50);
}

function showPhaseInfo(phase) {
 var info = phaseInfo[phase];
 if (!info) return;
 var panel = document.getElementById('detail-panel');
 if (!panel) return;
 if (active === 'phase-'+phase && panel.classList.contains('visible')) {
 panel.classList.remove('visible');
 active = null;
 return;
 }
 active = 'phase-'+phase;
 var iconEl = document.getElementById('detail-icon');
 var nameEl = document.getElementById('detail-name');
 var phaseEl = document.getElementById('detail-phase');
 var descEl = document.getElementById('detail-desc');
 var tagsEl = document.getElementById('detail-tags');
 var headerEl = document.getElementById('detail-header');
 if (iconEl) { iconEl.textContent = info.title ? info.title.split(' ')[1] : 'P'; iconEl.style.background = info.color; iconEl.style.color = info.border; iconEl.style.fontWeight = '700'; iconEl.style.fontSize = '12px'; }
 if (nameEl) nameEl.textContent = info.title;
 if (phaseEl) phaseEl.textContent = 'Click any node card for more details';
 if (descEl) { descEl.textContent = info.text; descEl.style.textAlign = 'justify'; }
 if (headerEl) headerEl.style.background = info.color;
 if (tagsEl) tagsEl.innerHTML = info.tags.map(function(t) {
 return '<span class="detail-tag">' + t + '</span>';
 }).join('');
 panel.classList.add('visible');
 setTimeout(function() {
 panel.scrollIntoView({behavior:'smooth', block:'nearest'});
 }, 50);
}

var phaseTrackPct = {p1:'0%', p2:'33%', p3:'66%', p4:'100%'};

function setPhase(phase) {
 var allBtn = document.getElementById('all-btn');
 if (allBtn) allBtn.classList.toggle('active', phase === 'all');
 ['1','2','3','4'].forEach(function(n, i) {
 var step = document.getElementById('ts'+n);
 if (!step) return;
 step.classList.remove('active','done');
 if (phase !== 'all') {
 var idx = parseInt(phase.replace('p',''));
 if (i+1 < idx) step.classList.add('done');
 else if (i+1 === idx) step.classList.add('active');
 }
 });
 var fill = document.getElementById('tl-fill');
 if (fill) fill.style.width = phase === 'all' ? '0%' : (phaseTrackPct[phase] || '0%');
 ['p1','p2','p3','p4'].forEach(function(p) {
 var el = document.getElementById('pg-'+p);
 if (el) el.classList.toggle('dimmed', phase !== 'all' && phase !== p);
 });
 var panel = document.getElementById('detail-panel');
 if (panel) panel.classList.remove('visible');
 active = null;
 if (phase !== 'all') showPhaseInfo(phase);
}
</script>

<style>
@keyframes flowAnim { to { stroke-dashoffset: -20; } }
@keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
@keyframes popIn { from{opacity:0;transform:scale(.88)} to{opacity:1;transform:scale(1)} }
@keyframes pulseRing { 0%{box-shadow:0 0 0 0 rgba(99,102,241,.4)} 70%{box-shadow:0 0 0 10px rgba(99,102,241,0)} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0)} }
@keyframes shimmer { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
@keyframes drawLine { from{stroke-dashoffset:300} to{stroke-dashoffset:0} }
* { box-sizing:border-box; margin:0; padding:0; }
.aw { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; padding:0 0 40px; }

/* timeline */
.tl-wrap {
 display:flex; align-items:center; gap:0;
 margin-bottom:32px; padding:0 10px;
 position:relative;
}
.tl-line {
 position:absolute; top:20px; left:10px; right:10px; height:2px;
 background:#e2e8f0; z-index:0; border-radius:2px;
}
.tl-line-fill {
 position:absolute; top:0; left:0; height:100%;
 background:linear-gradient(90deg,#6366f1,#8b5cf6);
 border-radius:2px; transition:width .5s cubic-bezier(.4,0,.2,1);
 width:0%;
}
.tl-step {
 display:flex; flex-direction:column; align-items:center; gap:8px;
 flex:1; position:relative; z-index:1; cursor:pointer;
}
.tl-circle {
 width:42px; height:42px; border-radius:50%;
 background:white; border:2px solid #e2e8f0;
 display:flex; align-items:center; justify-content:center;
 font-size:14px; font-weight:700; color:#94a3b8;
 transition:all .28s cubic-bezier(.4,0,.2,1);
 position:relative;
}
.tl-step:hover .tl-circle {
 border-color:#6366f1; color:#6366f1;
 transform:translateY(-2px);
 box-shadow:0 4px 14px rgba(99,102,241,.2);
}
.tl-step.active .tl-circle {
 background:#6366f1; border-color:#6366f1; color:white;
 transform:translateY(-3px) scale(1.1);
 animation:pulseRing 2s infinite;
 box-shadow:0 6px 20px rgba(99,102,241,.35);
}
.tl-step.done .tl-circle {
 background:#10b981; border-color:#10b981; color:white;
 transform:translateY(-2px);
 box-shadow:0 4px 12px rgba(16,185,129,.25);
}
.tl-label {
 font-size:11px; font-weight:500; color:#94a3b8;
 text-align:center; line-height:1.35; max-width:72px;
 transition:color .2s;
}
.tl-step:hover .tl-label { color:#6366f1; }
.tl-step.active .tl-label { color:#6366f1; font-weight:700; }
.tl-step.done .tl-label { color:#10b981; font-weight:600; }

.all-btn {
 padding:8px 20px; border-radius:22px;
 border:1.5px solid #e2e8f0; background:white;
 color:#64748b; font-size:12px; font-weight:600;
 cursor:pointer; font-family:inherit;
 transition:all .2s; white-space:nowrap; margin-right:16px;
 flex-shrink:0;
}
.all-btn:hover { border-color:#6366f1; color:#6366f1; background:#f5f3ff; }
.all-btn.active { background:#6366f1; color:white; border-color:#6366f1; box-shadow:0 4px 14px rgba(99,102,241,.3); }

/* canvas */
.canvas-wrap {
 position:relative; border-radius:16px;
 border:1px solid #e2e8f0; overflow:hidden;
 background:#fafafa;
 box-shadow:0 1px 3px rgba(0,0,0,.04),0 8px 32px rgba(0,0,0,.04);
}
.canvas-inner { padding:28px 24px 32px; }

/* phase group */
.phase-group {
 opacity:1; transition:opacity .4s ease, transform .4s ease;
}
.phase-group.dimmed { opacity:.07; pointer-events:none; }

.phase-header {
 display:flex; align-items:center; gap:10px; margin-bottom:14px;
}
.phase-dot {
 width:8px; height:8px; border-radius:50%; flex-shrink:0;
}
.phase-title {
 font-size:10px; font-weight:700; letter-spacing:.1em;
 text-transform:uppercase; color:#94a3b8;
}
.phase-divider {
 flex:1; height:1px; background:#f1f5f9; margin-left:4px;
}

/* node cards */
.node-row { display:flex; gap:10px; margin-bottom:10px; }
.node-card {
 flex:1; border-radius:12px; padding:13px 15px;
 cursor:pointer; position:relative; overflow:hidden;
 border:1px solid transparent;
 transition:all .22s cubic-bezier(.4,0,.2,1);
 animation:popIn .4s ease both;
}
.node-card::before {
 content:''; position:absolute; inset:0; border-radius:12px;
 background:linear-gradient(135deg,rgba(255,255,255,.6),transparent);
 pointer-events:none;
}
.node-card:hover {
 transform:translateY(-3px) scale(1.02);
 box-shadow:0 8px 24px rgba(0,0,0,.1);
 border-color:rgba(0,0,0,.08);
 z-index:2;
}
.node-card:active { transform:scale(.98); }
.node-card.selected { border-width:1.5px; box-shadow:0 0 0 3px rgba(99,102,241,.15); }
.node-title { font-size:13px; font-weight:700; margin-bottom:3px; }
.node-sub { font-size:11px; opacity:.75; line-height:1.4; text-align:justify; }
.node-badge {
 position:absolute; top:9px; right:10px;
 font-size:9px; font-weight:700; letter-spacing:.06em;
 padding:2px 7px; border-radius:8px;
 background:rgba(255,255,255,.55); backdrop-filter:blur(4px);
}
.node-full { flex:none; width:100%; }

/* hub node */
.hub-node {
 border-radius:10px; padding:11px 16px;
 display:flex; align-items:center; gap:12px;
 cursor:pointer; border:1px dashed #cbd5e1;
 background:white; transition:all .2s; margin-bottom:10px;
}
.hub-node:hover { border-color:#6366f1; background:#f5f3ff; transform:translateY(-1px); box-shadow:0 4px 14px rgba(99,102,241,.1); }
.hub-badge {
 width:30px; height:30px; border-radius:8px;
 background:linear-gradient(135deg,#6366f1,#8b5cf6);
 display:flex; align-items:center; justify-content:center;
 font-size:11px; font-weight:800; color:white; flex-shrink:0;
}
.hub-text { font-size:12px; font-weight:500; color:#334155; text-align:justify; }
.hub-sub { font-size:11px; color:#94a3b8; margin-top:1px; }

/* connector */
.connector {
 display:flex; justify-content:center; margin:2px 0;
}
.connector svg { overflow:visible; }

/* detail panel */
.detail-panel {
 display:none; margin-top:16px;
 border-radius:14px; overflow:hidden;
 animation:fadeUp .22s ease; border:1px solid #e2e8f0;
 box-shadow:0 4px 24px rgba(0,0,0,.07);
}
.detail-panel.visible { display:block; }
.detail-header {
 padding:14px 18px 12px;
 display:flex; align-items:center; gap:10px;
 border-bottom:1px solid #f1f5f9;
}
.detail-icon {
 width:34px; height:34px; border-radius:9px;
 display:flex; align-items:center; justify-content:center;
 font-size:15px; flex-shrink:0;
}
.detail-name { font-size:14px; font-weight:700; color:#0f172a; }
.detail-phase { font-size:11px; color:#94a3b8; margin-top:1px; }
.detail-body { padding:14px 18px; background:white; }
.detail-desc { font-size:13px; color:#475569; line-height:1.75; margin-bottom:12px; text-align:justify; }
.detail-tags { display:flex; flex-wrap:wrap; gap:6px; }
.detail-tag {
 font-size:11px; padding:3px 10px; border-radius:20px;
 background:#f1f5f9; color:#475569; font-family:monospace;
 border:1px solid #e2e8f0;
}
</style>

<div class="aw">
 <!-- timeline navigation -->
 <div class="tl-wrap">
 <button class="all-btn active" id="all-btn" onclick="setPhase('all')">All phases</button>
 <div class="tl-line"><div class="tl-line-fill" id="tl-fill"></div></div>
 <div class="tl-step" id="ts1" onclick="setPhase('p1')" style="cursor:pointer">
 <div class="tl-circle">1</div>
 <div class="tl-label">Data<br>ingestion</div>
 </div>
 <div class="tl-step" id="ts2" onclick="setPhase('p2')" style="cursor:pointer">
 <div class="tl-circle">2</div>
 <div class="tl-label">Cache<br>generation</div>
 </div>
 <div class="tl-step" id="ts3" onclick="setPhase('p3')" style="cursor:pointer">
 <div class="tl-circle">3</div>
 <div class="tl-label">Scoring<br>pipelines</div>
 </div>
 <div class="tl-step" id="ts4" onclick="setPhase('p4')" style="cursor:pointer">
 <div class="tl-circle">4</div>
 <div class="tl-label">Evaluation</div>
 </div>
 </div>

 <div class="canvas-wrap">
 <div class="canvas-inner">

 <!-- PHASE 1 -->
 <div class="phase-group" id="pg-p1">
 <div class="phase-header">
 <div class="phase-dot" style="background:#10b981"></div>
 <span class="phase-title">Phase 1 - Data ingestion</span>
 <div class="phase-divider"></div>
 </div>
 <div class="node-row">
 <div class="node-card" style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#a7f3d0" data-key="data-loader" onclick="showDetail('data-loader')">
 <div class="node-badge" style="color:#065f46">loader</div>
 <div class="node-title" style="color:#064e3b">data_loader.py</div>
 <div class="node-sub" style="color:#047857">Downloads CNN/DM, XSum, FaithBench raw data</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#a7f3d0" data-key="splitter" onclick="showDetail('splitter')">
 <div class="node-badge" style="color:#065f46">split</div>
 <div class="node-title" style="color:#064e3b">splitter.py</div>
 <div class="node-sub" style="color:#047857">70/15/15 train/val/test, seed=42</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#a7f3d0" data-key="labels" onclick="showDetail('labels')">
 <div class="node-badge" style="color:#065f46">label</div>
 <div class="node-title" style="color:#064e3b">faithbench_labels.py</div>
 <div class="node-sub" style="color:#047857">Binary hallucination labels, 800 rows</div>
 </div>
 </div>
 <div class="connector"><svg width="2" height="22"><line x1="1" y1="0" x2="1" y2="22" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 3" style="animation:flowAnim .8s linear infinite"/></svg></div>
 <div class="hub-node" data-key="hf-splits" onclick="showDetail('hf-splits')">
 <div class="hub-badge">HF</div>
 <div><div class="hub-text">factshield-team/cache + faithbench-labels</div><div class="hub-sub">cnndm_splits, xsum_splits, faithbench_splits</div></div>
 </div>
 </div>

 <!-- connector p1→p2 -->
 <div class="connector" style="margin:4px 0 8px"><svg width="2" height="28"><line x1="1" y1="0" x2="1" y2="28" stroke="#a5b4fc" stroke-width="2" stroke-dasharray="5 3" style="animation:flowAnim .9s linear infinite"/></svg></div>

 <!-- PHASE 2 -->
 <div class="phase-group" id="pg-p2">
 <div class="phase-header">
 <div class="phase-dot" style="background:#7c3aed"></div>
 <span class="phase-title">Phase 2 - Cache generation (Kaggle T4 GPU)</span>
 <div class="phase-divider"></div>
 </div>
 <div class="node-row">
 <div class="node-card node-full" style="background:linear-gradient(135deg,#ede9fe,#ddd6fe);border-color:#c4b5fd" data-key="generate" onclick="showDetail('generate')">
 <div class="node-badge" style="color:#4c1d95">GPU</div>
 <div class="node-title" style="color:#3b0764">generate.py - BART, T5, PEGASUS</div>
 <div class="node-sub" style="color:#6d28d9">beam search summaries, K=10 stochastic samples, token log-probs, batch_size=16, float16, torch.compile</div>
 </div>
 </div>
 <div class="connector"><svg width="2" height="22"><line x1="1" y1="0" x2="1" y2="22" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 3" style="animation:flowAnim .8s linear infinite"/></svg></div>
 <div class="hub-node" data-key="hf-cache" onclick="showDetail('hf-cache')">
 <div class="hub-badge">HF</div>
 <div><div class="hub-text">factshield-team/cache - 27 configs</div><div class="hub-sub">3 models × 3 datasets × 3 output types</div></div>
 </div>
 </div>

 <!-- connector p2→p3 -->
 <div class="connector" style="margin:4px 0 8px"><svg width="2" height="28"><line x1="1" y1="0" x2="1" y2="28" stroke="#a5b4fc" stroke-width="2" stroke-dasharray="5 3" style="animation:flowAnim .9s linear infinite"/></svg></div>

 <!-- PHASE 3 -->
 <div class="phase-group" id="pg-p3">
 <div class="phase-header">
 <div class="phase-dot" style="background:#ea580c"></div>
 <span class="phase-title">Phase 3 - Scoring pipelines (local)</span>
 <div class="phase-divider"></div>
 </div>
 <div class="node-row">
 <div class="node-card" style="background:linear-gradient(135deg,#fff7ed,#ffedd5);border-color:#fdba74" data-key="selfcheck" onclick="showDetail('selfcheck')">
 <div class="node-badge" style="color:#7c2d12">P1</div>
 <div class="node-title" style="color:#7c2d12">selfcheck pipeline</div>
 <div class="node-sub" style="color:#c2410c">BERTScore, NLI (DeBERTa), Ngram</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd" data-key="entailment" onclick="showDetail('entailment')">
 <div class="node-badge" style="color:#1e3a8a">P2</div>
 <div class="node-title" style="color:#1e3a8a">entailment pipeline</div>
 <div class="node-sub" style="color:#1d4ed8">MiniCheck, RoBERTa-large</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fcd34d" data-key="tokprob" onclick="showDetail('tokprob')">
 <div class="node-badge" style="color:#78350f">P3</div>
 <div class="node-title" style="color:#78350f">token prob pipeline</div>
 <div class="node-sub" style="color:#b45309">perplexity, entropy, NLL classifier</div>
 </div>
 </div>
 <div class="connector"><svg width="2" height="22"><line x1="1" y1="0" x2="1" y2="22" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 3" style="animation:flowAnim .8s linear infinite"/></svg></div>
 <div class="hub-node" data-key="hf-results" onclick="showDetail('hf-results')">
 <div class="hub-badge">HF</div>
 <div><div class="hub-text">factshield-team/results</div><div class="hub-sub">task1_scores, task2_scores, task3_scores</div></div>
 </div>
 </div>

 <!-- connector p3→p4 -->
 <div class="connector" style="margin:4px 0 8px"><svg width="2" height="28"><line x1="1" y1="0" x2="1" y2="28" stroke="#a5b4fc" stroke-width="2" stroke-dasharray="5 3" style="animation:flowAnim .9s linear infinite"/></svg></div>

 <!-- PHASE 4 -->
 <div class="phase-group" id="pg-p4">
 <div class="phase-header">
 <div class="phase-dot" style="background:#16a34a"></div>
 <span class="phase-title">Phase 4 - Evaluation</span>
 <div class="phase-divider"></div>
 </div>
 <div class="node-row">
 <div class="node-card" style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;flex:2" data-key="evaluate" onclick="showDetail('evaluate')">
 <div class="node-badge" style="color:#14532d">eval</div>
 <div class="node-title" style="color:#14532d">evaluate.py (per pipeline)</div>
 <div class="node-sub" style="color:#15803d">AUROC, AUPRC, F1, ECE - FaithBench only, 50/50 val/test</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;flex:2" data-key="final-table" onclick="showDetail('final-table')">
 <div class="node-badge" style="color:#14532d">final</div>
 <div class="node-title" style="color:#14532d">assemble_final_table.py</div>
 <div class="node-sub" style="color:#15803d">Merges all results, ranks by AUROC, pushes final_table</div>
 </div>
 <div class="node-card" style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;flex:1" data-key="validate" onclick="showDetail('validate')">
 <div class="node-badge" style="color:#14532d">CI</div>
 <div class="node-title" style="color:#14532d">validate_all.py</div>
 <div class="node-sub" style="color:#15803d">36/36 passed</div>
 </div>
 </div>
 </div>

 </div>
 </div>

 <!-- detail panel -->
 <div class="detail-panel" id="detail-panel">
 <div class="detail-header" id="detail-header">
 <div class="detail-icon" id="detail-icon"></div>
 <div><div class="detail-name" id="detail-name"></div><div class="detail-phase" id="detail-phase"></div></div>
 </div>
 <div class="detail-body">
 <div class="detail-desc" id="detail-desc"></div>
 <div class="detail-tags" id="detail-tags"></div>
 </div>
 </div>

</div>

"""

DOCS_HTML = """
<script>
function showDoc(id, btn) {
 document.querySelectorAll('.doc-panel').forEach(function(p) { p.classList.remove('visible'); });
 document.querySelectorAll('.docs-nav button').forEach(function(b) { b.classList.remove('active'); });
 var panel = document.getElementById('doc-' + id);
 if (panel) panel.classList.add('visible');
 if (btn) btn.classList.add('active');
}
</script>
"""

METHOD_LABELS = {
 "selfcheck_nli": "SelfCheck NLI",
 "selfcheck_bert": "SelfCheck BERTScore",
 "selfcheck_ngram": "SelfCheck Ngram",
 "minicheck": "Entailment MiniCheck",
 "token_prob_classifier": "Token Probability",
}

METHOD_COLOR = {
 "selfcheck_nli": "#f97316",
 "selfcheck_bert": "#fb923c",
 "selfcheck_ngram": "#fdba74",
 "minicheck": "#3b82f6",
 "token_prob_classifier": "#a855f7",
}

MODEL_ICON = {"bart": "B", "t5": "T", "pegasus": "P"}
MODEL_COLOR = {"bart": "#6366f1", "t5": "#10b981", "pegasus": "#f59e0b"}


_RESULTS_JS = """<script>
function filterRes(type, btn) {
 document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
 if (btn) btn.classList.add('active');
 document.querySelectorAll('.result-item').forEach(function(item) {
 var m = item.getAttribute('data-method') || '';
 var show = type === 'all' ||
 (type === 'selfcheck' && m.indexOf('selfcheck') !== -1) ||
 (type === 'entailment' && m === 'minicheck') ||
 (type === 'tokprob' && m === 'token_prob_classifier');
 var visibleDisplay = item.tagName === 'TR' ? 'table-row' : 'block';
 item.style.display = show ? visibleDisplay : 'none';
 });
}
function resultsInit() {
 var els = document.querySelectorAll('[data-width]');
 if (!els.length) { setTimeout(resultsInit, 200); return; }
 els.forEach(function(el) {
 setTimeout(function() { el.style.width = el.getAttribute('data-width'); }, 400);
 });
}
resultsInit();
</script>

<style>
.docs { font-family: sans-serif; padding: 0 0 24px; }
.docs-nav { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; border-bottom: 0.5px solid #e5e7eb; padding-bottom: 14px; }
.docs-nav button {
 background: none; border: none; color: #6b7280; font-size: 13px; cursor: pointer;
 padding: 4px 10px; border-radius: 6px; transition: all .15s; font-family: sans-serif;
}
.docs-nav button:hover { background: #f3f4f6; color: #111827; }
.docs-nav button.active { background: #f3f4f6; color: #111827; font-weight: 500; }
.doc-panel { display: none; animation: fadeIn .2s ease; }
.doc-panel.visible { display: block; }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
.doc-panel h2 { font-size: 16px; font-weight: 500; color: #111827; margin: 0 0 10px; }
.doc-panel p, .doc-panel li { font-size: 14px; color: #4b5563; line-height: 1.75; margin: 0 0 8px; }
.doc-panel ul { padding-left: 20px; margin: 8px 0; }
.tag { display: inline-block; background: #ede9fe; color: #6d28d9; font-size: 11px; padding: 2px 10px; border-radius: 20px; margin: 2px; }
.ftag { display: inline-block; background: #f1f5f9; color: #475569; font-size: 11px; padding: 2px 10px; border-radius: 6px; font-family: monospace; margin: 2px; }
.ref { font-size: 12px; color: #9ca3af; border-left: 2px solid #e5e7eb; padding-left: 10px; margin-top: 10px; }
.metric-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; margin: 12px 0; }
.metric-card { background: #f8fafc; border: 0.5px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; }
.metric-card .ml { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
.metric-card .mv { font-size: 15px; font-weight: 500; color: #1e293b; }
.metric-card .md { font-size: 12px; color: #64748b; margin-top: 2px; }
</style>
<div class="docs">
 <div class="docs-nav">
 <button class="active" data-doc="overview" onclick="showDoc('overview',this)">Overview</button>
 <button data-doc="pipeline1" onclick="showDoc('pipeline1',this)">Pipeline 1 - SelfCheck</button>
 <button data-doc="pipeline2" onclick="showDoc('pipeline2',this)">Pipeline 2 - Entailment</button>
 <button data-doc="pipeline3" onclick="showDoc('pipeline3',this)">Pipeline 3 - Token prob</button>
 <button data-doc="evaluation" onclick="showDoc('evaluation',this)">Evaluation</button>
 <button data-doc="infra" onclick="showDoc('infra',this)">Infrastructure</button>
 <button data-doc="refs" onclick="showDoc('refs',this)">References</button>
 </div>

 <div class="doc-panel visible" id="doc-overview">
 <h2>Project overview</h2>
 <p>FactShield is a hallucination detection benchmark comparing three lightweight detection methods across three summarization models and three datasets. The project evaluates whether token probability, entailment verification, and consistency-based scoring can reliably detect factual errors in LLM-generated summaries.</p>
 <p><b>Models:</b> <span class="tag">facebook/bart-base</span> <span class="tag">t5-small</span> <span class="tag">google/pegasus-large</span></p>
 <p><b>Datasets:</b> CNN/DailyMail (1400 docs), XSum (1400 docs), FaithBench (560 docs, labeled)</p>
 <p><b>Evaluation:</b> Only FaithBench has human hallucination annotations. CNN/DM and XSum are used for cross-domain score distribution analysis.</p>
 </div>

 <div class="doc-panel" id="doc-pipeline1">
 <h2>Pipeline 1 - SelfCheckGPT</h2>
 <p>Scores summary sentences for consistency across K=10 stochastic samples. The core idea: if a sentence is factual, the model will say similar things repeatedly. Inconsistency across samples signals hallucination.</p>
 <ul>
 <li><b>BERTScore</b> - semantic similarity between each sentence and the other K samples using contextual BERT embeddings</li>
 <li><b>NLI (DeBERTa)</b> - cross-encoder/nli-deberta-v3-large checks if the other K samples entail the sentence. Contradiction = likely hallucinated.</li>
 <li><b>Ngram</b> - unigram overlap probability. Low overlap means the sentence uses words not found in other samples.</li>
 </ul>
 <p><span class="ftag">selfcheck/pipeline.py</span> <span class="ftag">selfcheck/scorer.py</span> <span class="ftag">selfcheck/run.py</span></p>
 <div class="ref">Manakul et al., 2023 - SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection. arXiv:2303.08896</div>
 </div>

 <div class="doc-panel" id="doc-pipeline2">
 <h2>Pipeline 2 - Entailment verification</h2>
 <p>Scores each sentence against its source document. Unlike SelfCheckGPT which compares summaries against each other, entailment directly checks against the source - asking "is this sentence supported by the article?"</p>
 <ul>
 <li><b>MiniCheck</b> (RoBERTa-large, fine-tuned for factual consistency) - outputs probability 0-1 that the sentence is grounded in the source document</li>
 <li>Sentence-level scores aggregated to doc-level by mean</li>
 <li>Originally planned SummaC but vitc model unavailable - MiniCheck is faster and more accurate</li>
 </ul>
 <p><span class="ftag">entailment/pipeline.py</span> <span class="ftag">entailment/scorer.py</span> <span class="ftag">entailment/run.py</span></p>
 <div class="ref">Tang et al., 2024 - MiniCheck: Efficient Fact-Checking of LLMs. arXiv:2404.10774</div>
 </div>

 <div class="doc-panel" id="doc-pipeline3">
 <h2>Pipeline 3 - Token probability</h2>
 <p>Uses the model's own confidence during generation as a hallucination signal. When a model hallucinates, it generates tokens with lower probability - high uncertainty may indicate fabricated content.</p>
 <ul>
 <li><b>Perplexity</b> - exp(-mean(log_probs)) - overall generation difficulty</li>
 <li><b>Mean entropy</b> - average token-level uncertainty across the summary</li>
 <li><b>Max entropy</b> - the single most uncertain token - spikes may indicate hallucinated names or numbers</li>
 <li><b>Tail mean NLL</b> - average negative log-likelihood of the last 5 tokens - models become more uncertain toward the end of hallucinated content</li>
 <li><b>Sentence length</b> - longer summaries have more hallucination opportunity</li>
 </ul>
 <p>A logistic regression classifier is trained on these 5 features using FaithBench labels (cross-validation over C ∈ {0.01, 0.1, 1.0, 10.0}, sigmoid calibration).</p>
 <p><span class="ftag">token_prob/pipeline.py</span> <span class="ftag">token_prob/scorer.py</span> <span class="ftag">token_prob/classifier.py</span></p>
 <div class="ref">Guerreiro et al., 2023 - Hallucinations in Neural Machine Translation. arXiv:2208.05309</div>
 </div>

 <div class="doc-panel" id="doc-evaluation">
 <h2>Evaluation</h2>
 <div class="metric-grid">
 <div class="metric-card"><div class="ml">AUROC</div><div class="mv">Ranking quality</div><div class="md">Area under ROC curve. 0.5 = random, 1.0 = perfect.</div></div>
 <div class="metric-card"><div class="ml">AUPRC</div><div class="mv">Precision-recall</div><div class="md">Better than AUROC for imbalanced labels.</div></div>
 <div class="metric-card"><div class="ml">F1</div><div class="mv">Best threshold</div><div class="md">Threshold tuned on val set, applied to test - no data leakage.</div></div>
 <div class="metric-card"><div class="ml">ECE</div><div class="mv">Calibration</div><div class="md">Expected calibration error. Lower = better-calibrated probabilities.</div></div>
 </div>
 <p>Only FaithBench docs are evaluated (the only dataset with human hallucination annotations). CNN/DM and XSum produce scores but have no ground truth labels. A 50/50 val/test split is used since all results are stored with split='test'.</p>
 </div>

 <div class="doc-panel" id="doc-infra">
 <h2>Infrastructure</h2>
 <ul>
 <li><b>Cache generation</b> - Kaggle T4 GPU (free tier, 30hr/week). All 27 configs generated in ~6 sessions.</li>
 <li><b>Storage</b> - HuggingFace Hub. factshield-team/cache (27 configs), factshield-team/results (4 configs), factshield-team/faithbench-labels, factshield-team/fs_models.</li>
 <li><b>CI/CD</b> - GitHub Actions with 4 jobs: Flake8 lint → unit tests → coverage (60% threshold) → evaluation.</li>
 <li><b>Tests</b> - 104 tests across test_cache.py, test_results.py, test_scorer.py, test_evaluate.py, test_data.py.</li>
 <li><b>Validation</b> - validate_all.py checks all 36 Hub artifacts. 36/36 passed.</li>
 </ul>
 </div>

 <div class="doc-panel" id="doc-refs">
 <h2>References</h2>
 <ul>
 <li>Manakul et al., 2023 - SelfCheckGPT. arXiv:2303.08896</li>
 <li>Tang et al., 2024 - MiniCheck. arXiv:2404.10774</li>
 <li>Guerreiro et al., 2023 - Hallucinations in NMT. arXiv:2208.05309</li>
 <li>Laban et al., 2022 - SummaC. arXiv:2111.09525</li>
 <li>Hermann et al., 2015 - CNN/DailyMail. arXiv:1506.03340</li>
 <li>Narayan et al., 2018 - XSum. arXiv:1808.08745</li>
 <li>Vectara, 2024 - FaithBench. github.com/vectara/FaithBench</li>
 <li>Wolf et al., 2020 - HuggingFace Transformers. arXiv:1910.03771</li>
 <li>Zhang et al., 2020 - BERTScore. arXiv:1904.09675</li>
 </ul>
 </div>
</div>
"""


def build_results_html(df):
    if "error" in df.columns:
        return f"<p style='color:red;font-family:sans-serif'>Error: {df['error'][0]}</p>"

    df = df.sort_values("AUROC", ascending=False).reset_index(drop=True)
    best = df.iloc[0]
    max_auroc = df["AUROC"].max()
    min_auroc = df["AUROC"].min()
    auroc_range = max_auroc - min_auroc if max_auroc != min_auroc else 0.01

    best_method_label = METHOD_LABELS.get(best["method"], best["method"])

    podium_rows = df.head(3)
    podium_html = ""
    podium_orders = [1, 0, 2]
    podium_heights = ["80px", "110px", "60px"]
    podium_medals = ["#2", "#1", "#3"]
    podium_items = [podium_rows.iloc[i] if i < len(podium_rows) else None for i in podium_orders]

    for i, (item, h, medal) in enumerate(zip(podium_items, podium_heights, podium_medals)):
        if item is None:
            podium_html += "<div></div>"
            continue
        mc = METHOD_COLOR.get(item["method"], "#94a3b8")
        mlabel = METHOD_LABELS.get(item["method"], item["method"])
        mcolor = MODEL_COLOR.get(item["summarizer"], "#6b7280")
        delay = i * 0.1
        podium_html += f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:8px;animation:riseUp .6s {delay}s ease both">
        <div style="font-size:13px;font-weight:700;color:#64748b;background:#f1f5f9;border-radius:20px;padding:3px 10px">{medal}</div>
        <div style="background:white;border:0.5px solid #e2e8f0;border-top:3px solid {mc};border-radius:12px;padding:14px 16px;text-align:center;min-width:140px;box-shadow:0 2px 12px rgba(0,0,0,0.06)">
        <div style="font-size:22px;font-weight:600;color:{mc}">{item['AUROC']:.4f}</div>
        <div style="font-size:12px;font-weight:500;color:#1e293b;margin:4px 0 2px">{mlabel}</div>
        <div style="display:inline-flex;align-items:center;gap:4px;background:{mcolor}18;border-radius:20px;padding:2px 10px">
        <span style="width:16px;height:16px;border-radius:50%;background:{mcolor};color:white;font-size:9px;font-weight:600;display:inline-flex;align-items:center;justify-content:center">{MODEL_ICON.get(item['summarizer'],'?')}</span>
        <span style="font-size:11px;color:{mcolor};font-weight:500">{item['summarizer'].upper()}</span>
        </div>
        </div>
        <div style="background:{mc};border-radius:6px 6px 0 0;width:100%;height:{h};opacity:0.15"></div>
        </div>"""

    radar_data = []
    methods_seen = {}
    for _, row in df.iterrows():
        m = row["method"]
        if m not in methods_seen:
            methods_seen[m] = row
    for m, row in methods_seen.items():
        pct = round(((row["AUROC"] - min_auroc) / auroc_range) * 80 + 20)
        mc = METHOD_COLOR.get(m, "#94a3b8")
        label = METHOD_LABELS.get(m, m)
        radar_data.append((label, pct, mc, row["AUROC"]))

    method_bullets = {
    "selfcheck_nli": [
    "Strongest signal overall across all 3 models",
    "Checks if K=10 samples entail each sentence via DeBERTa",
    "Best with PEGASUS - more diverse samples = stronger signal",
    ],
    "selfcheck_bert": [
    "Semantic similarity between sentence and K samples",
    "Weaker than NLI - similarity is not the same as entailment",
    "Consistent across models but lower AUROC than NLI",
    ],
    "selfcheck_ngram": [
    "Unigram overlap probability across K samples",
    "Lowest sample count after inf filtering - less reliable",
    "Fastest to compute but least discriminative",
    ],
    "minicheck": [
    "Checks each sentence directly against the source document",
    "Uses RoBERTa-large fine-tuned for factual consistency",
    "Score ~1 = grounded in source, ~0 = hallucinated",
    ],
    "token_prob_classifier": [
    "Uses model uncertainty during generation as hallucination signal",
    "Competitive with entailment for T5 - useful for smaller models",
    "max_entropy and tail_mean_nll are the most predictive features",
    ],
    }

    radar_bars = ""
    for label, pct, mc, auroc in sorted(radar_data, key=lambda x: x[3], reverse=True):
        method_key = next((k for k, v in METHOD_LABELS.items() if v == label), "")
        bullets = method_bullets.get(method_key, [])
        bullets_html = "".join(
        f"""<li style="font-size:11px;color:#64748b;line-height:1.6;margin-bottom:2px">{b}</li>"""
    for b in bullets
        )
        radar_bars += f"""
        <div style="margin-bottom:18px;border-bottom:0.5px solid #f1f5f9;padding-bottom:14px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
        <span style="font-size:12px;font-weight:500;color:#334155">{label}</span>
        <span style="font-size:13px;font-weight:600;color:{mc}">{auroc:.4f}</span>
        </div>
        <div style="background:#f1f5f9;border-radius:6px;height:8px;overflow:hidden;margin-bottom:8px">
        <div style="height:100%;width:0;border-radius:6px;background:linear-gradient(90deg,{mc}88,{mc});transition:width 1.2s cubic-bezier(.4,0,.2,1)" data-width="{pct}%"></div>
        </div>
        <ul style="margin:0;padding-left:16px;list-style-type:disc">{bullets_html}</ul>
        </div>"""

    model_cards = ""
    for model in ["bart", "t5", "pegasus"]:
        model_df = df[df["summarizer"] == model]
        if model_df.empty:
            continue
        best_m = model_df.iloc[0]
        mc = MODEL_COLOR.get(model, "#6b7280")
        mlabel = METHOD_LABELS.get(best_m["method"], best_m["method"])
        model_cards += f"""
      <div style="background:white;border:0.5px solid #e2e8f0;border-radius:12px;padding:16px;flex:1;min-width:140px;animation:fadeUp .4s ease">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <div style="width:32px;height:32px;border-radius:50%;background:{mc};color:white;font-size:13px;font-weight:600;display:flex;align-items:center;justify-content:center">{MODEL_ICON.get(model,'?')}</div>
      <div>
      <div style="font-size:13px;font-weight:500;color:#1e293b">{model.upper()}</div>
      <div style="font-size:11px;color:#94a3b8">{len(model_df)} configs</div>
      </div>
      </div>
      <div style="font-size:26px;font-weight:600;color:{mc};margin-bottom:2px">{best_m['AUROC']:.4f}</div>
      <div style="font-size:11px;color:#64748b">best: {mlabel}</div>
      <div style="margin-top:10px;background:#f8fafc;border-radius:6px;padding:6px 10px">
      <div style="font-size:10px;color:#94a3b8;margin-bottom:3px">AUROC range</div>
      <div style="background:#e2e8f0;border-radius:3px;height:4px;overflow:hidden">
      <div style="height:100%;background:{mc};width:{round(((best_m['AUROC']-min_auroc)/auroc_range)*100)}%"></div>
      </div>
      </div>
      </div>"""

    table_rows = ""
    for rank, (_, row) in enumerate(df.iterrows(), 1):
        mc = METHOD_COLOR.get(row["method"], "#94a3b8")
        mlabel = METHOD_LABELS.get(row["method"], row["method"])
        mcolor = MODEL_COLOR.get(row["summarizer"], "#6b7280")
        pct = round(((row["AUROC"] - min_auroc) / auroc_range) * 100)
        is_best = rank == 1
        row_bg = "#fffbf5" if is_best else "white"
        rank_badge = f'<span style="background:{mc};color:white;font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px">#{rank}</span>'
        table_rows += f"""
      <tr class="result-item" data-method="{row['method']}" style="border-bottom:0.5px solid #f1f5f9;background:{row_bg};transition:background .15s" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='{row_bg}'">
      <td style="padding:12px 14px;font-size:12px">{rank_badge}</td>
      <td style="padding:12px 14px">
      <div style="font-size:13px;font-weight:500;color:#1e293b">{mlabel}</div>
      <div style="display:flex;align-items:center;gap:4px;margin-top:3px">
      <span style="width:14px;height:14px;border-radius:50%;background:{mcolor};color:white;font-size:8px;font-weight:600;display:inline-flex;align-items:center;justify-content:center">{MODEL_ICON.get(row['summarizer'],'?')}</span>
      <span style="font-size:11px;color:#94a3b8">{row['summarizer'].upper()}</span>
      </div>
      </td>
      <td style="padding:12px 14px">
      <div style="display:flex;align-items:center;gap:8px">
      <span style="font-size:15px;font-weight:600;color:{mc}">{row['AUROC']:.4f}</span>
      <div style="flex:1;background:#f1f5f9;border-radius:3px;height:5px;overflow:hidden;min-width:60px">
      <div style="height:100%;width:{pct}%;background:{mc};border-radius:3px"></div>
      </div>
      </div>
      </td>
      <td style="padding:12px 14px;font-size:13px;color:#64748b">{row['AUPRC']:.4f}</td>
      <td style="padding:12px 14px;font-size:12px;color:#94a3b8">{int(row['n_samples'])}</td>
      </tr>"""

    verdict_color = "#059669"
    verdict_bg = "#f0fdf4"
    verdict_border = "#86efac"

    html = f"""
{_RESULTS_JS}
<style>
@keyframes fadeUp {{ from{{opacity:0;transform:translateY(10px)}} to{{opacity:1;transform:translateY(0)}} }}
@keyframes riseUp {{ from{{opacity:0;transform:translateY(20px)}} to{{opacity:1;transform:translateY(0)}} }}
@keyframes shimmer {{ 0%{{background-position:-200% center}} 100%{{background-position:200% center}} }}
@keyframes countUp {{ from{{opacity:0;transform:scale(.8)}} to{{opacity:1;transform:scale(1)}} }}
* {{ box-sizing:border-box; }}
.db {{ font-family:sans-serif; padding:0 0 32px; }}
.section-title {{ font-size:11px;font-weight:600;letter-spacing:.08em;color:#94a3b8;text-transform:uppercase;margin:28px 0 14px; }}
</style>

<div class="db">

    <div style="background:{verdict_bg};border:0.5px solid {verdict_border};border-radius:16px;padding:20px 24px;margin-bottom:28px;animation:fadeUp .4s ease;position:relative;overflow:hidden">
    <div style="position:absolute;top:0;right:0;width:200px;height:100%;background:linear-gradient(135deg,transparent 60%,{verdict_color}08);pointer-events:none"></div>
    <div style="font-size:10px;font-weight:600;letter-spacing:.1em;color:{verdict_color};margin-bottom:6px">VERDICT - BEST HALLUCINATION DETECTOR</div>
    <div style="font-size:28px;font-weight:600;color:#14532d;margin-bottom:4px">{best_method_label} + {best["summarizer"].upper()}</div>
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <span style="font-size:32px;font-weight:700;color:{verdict_color};animation:countUp .6s .2s ease both">{best["AUROC"]:.4f}</span>
    <div>
    <div style="font-size:12px;color:#15803d;font-weight:500">AUROC on FaithBench</div>
    <div style="font-size:11px;color:#4ade80">{int(best["n_samples"])} test samples, highest across all {len(df)} configurations</div>
    </div>
    </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:28px">
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:12px;padding:14px 16px;animation:fadeUp .3s .05s ease both">
    <div style="font-size:10px;font-weight:600;letter-spacing:.06em;color:#94a3b8;margin-bottom:6px">BEST AUROC</div>
    <div style="font-size:26px;font-weight:600;color:#1e293b">{max_auroc:.4f}</div>
    <div style="font-size:11px;color:#64748b;margin-top:2px">{best["summarizer"].upper()} / {best_method_label}</div>
    </div>
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:12px;padding:14px 16px;animation:fadeUp .3s .1s ease both">
    <div style="font-size:10px;font-weight:600;letter-spacing:.06em;color:#94a3b8;margin-bottom:6px">CONFIGURATIONS</div>
    <div style="font-size:26px;font-weight:600;color:#1e293b">{len(df)}</div>
    <div style="font-size:11px;color:#64748b;margin-top:2px">method × model combos</div>
    </div>
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:12px;padding:14px 16px;animation:fadeUp .3s .15s ease both">
    <div style="font-size:10px;font-weight:600;letter-spacing:.06em;color:#94a3b8;margin-bottom:6px">BEST METHOD</div>
    <div style="font-size:16px;font-weight:600;color:#f97316;margin:4px 0">SelfCheck NLI</div>
    <div style="font-size:11px;color:#64748b">strongest signal overall</div>
    </div>
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:12px;padding:14px 16px;animation:fadeUp .3s .2s ease both">
    <div style="font-size:10px;font-weight:600;letter-spacing:.06em;color:#94a3b8;margin-bottom:6px">VALIDATION</div>
    <div style="font-size:26px;font-weight:600;color:#10b981">36/36</div>
    <div style="font-size:11px;color:#64748b;margin-top:2px">Hub artifact checks</div>
    </div>
    </div>

    <div class="section-title">Leaderboard - top 3</div>
    <div style="display:flex;align-items:flex-end;justify-content:center;gap:16px;padding:20px 0 0;margin-bottom:28px">
    {podium_html}
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px">
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:14px;padding:18px 20px;animation:fadeUp .4s ease">
    <div class="section-title" style="margin-top:0">Method comparison</div>
    {radar_bars}
    </div>
    <div style="background:white;border:0.5px solid #e2e8f0;border-radius:14px;padding:18px 20px;animation:fadeUp .4s .1s ease">
    <div class="section-title" style="margin-top:0">Best per model</div>
    <div style="display:flex;flex-direction:column;gap:10px">
    {model_cards}
    </div>
    </div>
    </div>

    <div style="background:#fffbeb;border:0.5px solid #fde68a;border-radius:12px;padding:16px 20px;margin-bottom:24px;font-size:13px;color:#92400e;line-height:1.8;text-align:justify;animation:fadeUp .4s ease">
    <span style="font-weight:600;color:#78350f">Key findings - </span>
    All methods perform modestly above random (0.5 baseline), consistent with the literature on FaithBench.
    <span style="font-weight:600">NLI-based consistency scoring</span> is the strongest signal - especially with PEGASUS which generates more diverse stochastic samples.
    <span style="font-weight:600">Token probability</span> is surprisingly competitive with entailment for T5, suggesting model uncertainty is a useful proxy for smaller models.
    BART is the hardest summarizer to detect hallucinations in across all methods.
    </div>

    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
    <button class="filter-btn active" onclick="filterRes(\'all\',this)" style="padding:6px 16px;border-radius:20px;border:1px solid #0f172a;background:#0f172a;color:white;font-size:12px;font-weight:600;cursor:pointer;font-family:sans-serif">All methods</button>
    <button class="filter-btn" onclick="filterRes(\'selfcheck\',this)" style="padding:6px 16px;border-radius:20px;border:1px solid #e2e8f0;background:white;color:#64748b;font-size:12px;font-weight:600;cursor:pointer;font-family:sans-serif">SelfCheck</button>
    <button class="filter-btn" onclick="filterRes(\'entailment\',this)" style="padding:6px 16px;border-radius:20px;border:1px solid #e2e8f0;background:white;color:#64748b;font-size:12px;font-weight:600;cursor:pointer;font-family:sans-serif">Entailment</button>
    <button class="filter-btn" onclick="filterRes(\'tokprob\',this)" style="padding:6px 16px;border-radius:20px;border:1px solid #e2e8f0;background:white;color:#64748b;font-size:12px;font-weight:600;cursor:pointer;font-family:sans-serif">Token prob</button>
    </div>
    <div class="section-title">Full results table</div>
    <div style="border:0.5px solid #e2e8f0;border-radius:12px;overflow:hidden;animation:fadeUp .4s ease">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead>
    <tr style="background:#f8fafc;border-bottom:0.5px solid #e2e8f0">
    <th style="padding:11px 14px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;color:#94a3b8">RANK</th>
    <th style="padding:11px 14px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;color:#94a3b8">METHOD / MODEL</th>
    <th style="padding:11px 14px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;color:#94a3b8">AUROC</th>
    <th style="padding:11px 14px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;color:#94a3b8">AUPRC</th>
    <th style="padding:11px 14px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;color:#94a3b8">N</th>
    </tr>
    </thead>
    <tbody>{table_rows}</tbody>
    </table>
    </div>

</div>
"""
    return html


def load_and_render_results():
    try:
        df = load_dataset("factshield-team/results", "final_table")["train"].to_pandas()
        return build_results_html(df)
    except Exception as e:
        return f"<p style='color:red;font-family:sans-serif'>Error loading results: {e}</p>"


MODELS_TAB_HTML = """
<script>
function showModel(name) {
  document.querySelectorAll('.model-btn').forEach(function(b) { b.classList.remove('active'); });
  document.querySelectorAll('.model-panel').forEach(function(p) { p.style.display = 'none'; });
  var btn = document.getElementById('btn-' + name);
  var panel = document.getElementById('panel-' + name);
  if (btn) btn.classList.add('active');
  if (panel) panel.style.display = 'block';
}
</script>

<style>
.mt-wrap { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 0 0 40px; }
.mt-header { margin-bottom: 24px; }
.mt-header h2 { font-size: 18px; font-weight: 600; color: #0f172a; margin-bottom: 6px; }
.mt-header p { font-size: 14px; color: #64748b; line-height: 1.7; text-align: justify; }
.model-selector { display: flex; gap: 12px; margin-bottom: 28px; }
.model-btn {
  flex: 1; padding: 16px 12px; border-radius: 12px; cursor: pointer;
  border: 1.5px solid #e2e8f0; background: white;
  font-family: inherit; text-align: center; transition: all .2s;
}
.model-btn:hover { border-color: #94a3b8; transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.08); }
.model-btn.active { border-width: 2px; transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.1); }
.model-btn .mb-initial {
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; color: white; margin: 0 auto 10px;
}
.model-btn .mb-name { font-size: 14px; font-weight: 600; color: #1e293b; }
.model-btn .mb-id { font-size: 11px; color: #94a3b8; margin-top: 3px; font-family: monospace; }
.model-btn .mb-tag { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 10px; margin-top: 6px; display: inline-block; }

.model-panel { display: none; animation: fadeUp .25s ease; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.panel-hero {
  border-radius: 14px; padding: 20px 24px; margin-bottom: 20px;
  display: flex; align-items: center; gap: 18px;
}
.panel-hero-icon {
  width: 56px; height: 56px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; color: white;
}
.panel-hero-title { font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
.panel-hero-sub { font-size: 13px; color: #64748b; }
.panel-hero-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.hero-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: rgba(255,255,255,.7); font-weight: 500; }

.section-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.section-card {
  background: white; border: 0.5px solid #e2e8f0; border-radius: 12px;
  padding: 16px 18px; transition: box-shadow .2s;
}
.section-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.06); }
.section-card.full { grid-column: 1 / -1; }
.sc-label {
  font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
}
.sc-label-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.sc-title { font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 6px; }
.sc-text { font-size: 13px; color: #475569; line-height: 1.75; text-align: justify; }
.sc-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.sc-tag { font-size: 11px; padding: 3px 9px; border-radius: 20px; background: #f1f5f9; color: #475569; border: 0.5px solid #e2e8f0; font-family: monospace; }

.score-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
.score-table th { padding: 8px 12px; text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .06em; color: #94a3b8; background: #f8fafc; border-bottom: 0.5px solid #e2e8f0; }
.score-table td { padding: 10px 12px; border-bottom: 0.5px solid #f1f5f9; color: #334155; }
.score-table tr:last-child td { border-bottom: none; }
.score-table tr:hover td { background: #f8fafc; }
.score-val { font-size: 15px; font-weight: 600; }
.score-bar-wrap { background: #f1f5f9; border-radius: 4px; height: 6px; overflow: hidden; margin-top: 4px; min-width: 80px; }
.score-bar { height: 100%; border-radius: 4px; }

.verdict-box {
  border-radius: 12px; padding: 16px 20px; margin-bottom: 14px;
  border-left: 4px solid;
}
.verdict-title { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 6px; }
.verdict-text { font-size: 13px; line-height: 1.75; text-align: justify; }

.step-list { list-style: none; padding: 0; margin: 0; }
.step-list li {
  display: flex; gap: 12px; padding: 10px 0; border-bottom: 0.5px solid #f1f5f9;
  font-size: 13px; color: #475569; line-height: 1.6;
}
.step-list li:last-child { border-bottom: none; }
.step-num {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: white; margin-top: 1px;
}
</style>

<div class="mt-wrap">
  <div class="mt-header">
    <h2>Model deep dives</h2>
    <p>Select a summarization model to see the complete breakdown of how summaries were generated, how they were scored across all three pipelines, and what the evaluation results show.</p>
  </div>

  <div class="model-selector">
    <div class="model-btn" id="btn-bart" onclick="showModel('bart')">
      <div class="mb-initial" style="background:#6366f1">B</div>
      <div class="mb-name">BART</div>
      <div class="mb-id">facebook/bart-base</div>
      <div class="mb-tag" style="background:#ede9fe;color:#6d28d9">406M params</div>
    </div>
    <div class="model-btn" id="btn-t5" onclick="showModel('t5')">
      <div class="mb-initial" style="background:#10b981">T</div>
      <div class="mb-name">T5</div>
      <div class="mb-id">t5-small</div>
      <div class="mb-tag" style="background:#d1fae5;color:#065f46">60M params</div>
    </div>
    <div class="model-btn" id="btn-pegasus" onclick="showModel('pegasus')">
      <div class="mb-initial" style="background:#f59e0b">P</div>
      <div class="mb-name">PEGASUS</div>
      <div class="mb-id">google/pegasus-large</div>
      <div class="mb-tag" style="background:#fef3c7;color:#92400e">568M params</div>
    </div>
  </div>

  <!-- BART PANEL -->
  <div class="model-panel" id="panel-bart">
    <div class="panel-hero" style="background:linear-gradient(135deg,#ede9fe,#ddd6fe)">
      <div class="panel-hero-icon" style="background:#6366f1">B</div>
      <div>
        <div class="panel-hero-title">BART - Bidirectional Auto-Regressive Transformer</div>
        <div class="panel-hero-sub">facebook/bart-base, encoder-decoder, denoising pre-training</div>
        <div class="panel-hero-badges">
          <span class="hero-badge" style="color:#4c1d95">406M parameters</span>
          <span class="hero-badge" style="color:#4c1d95">Seq2Seq</span>
          <span class="hero-badge" style="color:#4c1d95">Denoising pre-training</span>
          <span class="hero-badge" style="color:#4c1d95">1024 token context</span>
        </div>
      </div>
    </div>

    <div class="verdict-box" style="background:#faf5ff;border-color:#7c3aed">
      <div class="verdict-title" style="color:#7c3aed">Architecture overview</div>
      <div class="verdict-text" style="color:#4c1d95">BART combines a bidirectional encoder (like BERT) with a left-to-right auto-regressive decoder (like GPT). It is pre-trained by corrupting text with various noise functions and learning to reconstruct the original. This makes it well suited for sequence-to-sequence tasks like summarization. BART-base uses 6 encoder and 6 decoder layers with hidden size 768.</div>
    </div>

    <div class="section-grid">
      <div class="section-card">
        <div class="sc-label" style="color:#6366f1"><div class="sc-label-dot" style="background:#6366f1"></div>Summary generation</div>
        <div class="sc-title">How summaries were generated</div>
        <div class="sc-text">Beam search with num_beams=4 for deterministic summaries. K=10 stochastic samples with temperature=1.0 for SelfCheckGPT consistency scoring. Greedy decoding with output_scores=True for token log-probabilities. All generation used max_new_tokens=128, float16 precision, and batch_size=16 on Kaggle T4 GPU.</div>
        <div class="sc-tags">
          <span class="sc-tag">num_beams=4</span>
          <span class="sc-tag">K=10 samples</span>
          <span class="sc-tag">temperature=1.0</span>
          <span class="sc-tag">max_new_tokens=128</span>
          <span class="sc-tag">float16</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#6366f1"><div class="sc-label-dot" style="background:#6366f1"></div>Datasets covered</div>
        <div class="sc-title">3 datasets, 4,360 total documents</div>
        <div class="sc-text">CNN/DailyMail (1,400 docs): news articles with multi-sentence summaries. XSum (1,400 docs): BBC news with single-sentence abstracts. FaithBench (560 docs): LLM-generated summaries with human hallucination annotations. All datasets split 70/15/15 with seed=42.</div>
        <div class="sc-tags">
          <span class="sc-tag">cnndm 1,400</span>
          <span class="sc-tag">xsum 1,400</span>
          <span class="sc-tag">faithbench 560</span>
          <span class="sc-tag">seed=42</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#ea580c"><div class="sc-label-dot" style="background:#ea580c"></div>Pipeline 1 - SelfCheckGPT</div>
        <div class="sc-title">Consistency-based hallucination scoring</div>
        <div class="sc-text">Each sentence in the beam-search summary is scored for consistency against K=4 other stochastic samples. If a sentence is factual, the model will say similar things repeatedly across samples. Three scoring modes: BERTScore (semantic similarity), NLI via cross-encoder/nli-deberta-v3-large (entailment check), Ngram (unigram overlap probability). Sentence-level scores are averaged to doc-level.</div>
        <div class="sc-tags">
          <span class="sc-tag">BERTScore</span>
          <span class="sc-tag">NLI DeBERTa</span>
          <span class="sc-tag">Ngram n=1</span>
          <span class="sc-tag">30,237 rows</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#2563eb"><div class="sc-label-dot" style="background:#2563eb"></div>Pipeline 2 - Entailment</div>
        <div class="sc-title">Source-grounded factual verification</div>
        <div class="sc-text">Each sentence in the beam-search summary is checked against the source article using MiniCheck (roberta-large fine-tuned for factual consistency). Score near 1 means the sentence is entailed by the source, near 0 means it is not supported. Unlike SelfCheckGPT, this directly checks against ground truth rather than comparing across samples.</div>
        <div class="sc-tags">
          <span class="sc-tag">MiniCheck</span>
          <span class="sc-tag">roberta-large</span>
          <span class="sc-tag">sentence-level</span>
          <span class="sc-tag">10,080 rows</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#d97706"><div class="sc-label-dot" style="background:#d97706"></div>Pipeline 3 - Token probability</div>
        <div class="sc-title">Model uncertainty as hallucination signal</div>
        <div class="sc-text">Token log-probabilities from greedy decoding are decoded to float32. Five features extracted per document: perplexity (exp(-mean(log_probs))), mean entropy, max entropy (most uncertain token), tail mean NLL (last 5 tokens), and sentence length. A logistic regression classifier is trained on FaithBench labels with C cross-validated over {0.01, 0.1, 1.0, 10.0} and sigmoid calibration applied.</div>
        <div class="sc-tags">
          <span class="sc-tag">perplexity</span>
          <span class="sc-tag">mean entropy</span>
          <span class="sc-tag">max entropy</span>
          <span class="sc-tag">tail NLL</span>
          <span class="sc-tag">LogisticRegression</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Evaluation results</div>
        <div class="sc-title">BART AUROC on FaithBench</div>
        <table class="score-table">
          <thead><tr><th>Method</th><th>AUROC</th><th>AUPRC</th></tr></thead>
          <tbody>
            <tr><td>SelfCheck NLI</td><td><span class="score-val" style="color:#ea580c">0.4630</span><div class="score-bar-wrap"><div class="score-bar" style="width:82%;background:#ea580c"></div></div></td><td>0.6412</td></tr>
            <tr><td>SelfCheck BERTScore</td><td><span class="score-val" style="color:#ea580c">0.4437</span><div class="score-bar-wrap"><div class="score-bar" style="width:78%;background:#ea580c"></div></div></td><td>0.6330</td></tr>
            <tr><td>MiniCheck</td><td><span class="score-val" style="color:#2563eb">0.4820</span><div class="score-bar-wrap"><div class="score-bar" style="width:85%;background:#2563eb"></div></div></td><td>0.6433</td></tr>
            <tr><td>Token probability</td><td><span class="score-val" style="color:#d97706">0.4622</span><div class="score-bar-wrap"><div class="score-bar" style="width:82%;background:#d97706"></div></div></td><td>0.6719</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card full" style="margin-bottom:14px">
      <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Validation steps</div>
      <div class="sc-title">End-to-end verification for BART</div>
      <ul class="step-list">
        <li><div class="step-num" style="background:#6366f1">1</div><div>Cache generated on Kaggle T4 GPU. 3 configs pushed to Hub: bart_cnndm_summaries, bart_xsum_summaries, bart_faithbench_summaries (beam search), plus k_samples and token_scores equivalents. Total 9 BART configs.</div></li>
        <li><div class="step-num" style="background:#ea580c">2</div><div>SelfCheckGPT pipeline ran locally. 30,237 sentence-level scores across all 3 datasets and 3 modes. Results appended to task1_scores on Hub using drop_duplicates to prevent overwriting.</div></li>
        <li><div class="step-num" style="background:#2563eb">3</div><div>Entailment pipeline ran with MiniCheck. 10,080 sentence-level scores across 3 datasets. Mean-aggregated to doc-level for evaluation.</div></li>
        <li><div class="step-num" style="background:#d97706">4</div><div>Token probability pipeline extracted 5 features per doc. Classifier trained on BART FaithBench split. Best C=10.0, AUROC 0.4941 on cross-validation. Model pushed to factshield-team/fs_models.</div></li>
        <li><div class="step-num" style="background:#16a34a">5</div><div>Evaluation computed on FaithBench only (labeled dataset). 50/50 val/test split with threshold tuned on val. AUROC, AUPRC, F1, ECE computed. validate_all.py confirms all 9 BART Hub configs present and non-empty.</div></li>
      </ul>
    </div>

    <div class="verdict-box" style="background:#fef2f2;border-color:#ef4444">
      <div class="verdict-title" style="color:#dc2626">Key finding - BART</div>
      <div class="verdict-text" style="color:#7f1d1d">BART has the lowest AUROC across all methods compared to T5 and PEGASUS. MiniCheck (0.4820) is the strongest detector for BART summaries, slightly outperforming SelfCheckGPT NLI (0.4630). The relatively low scores suggest BART-generated hallucinations are harder to detect with lightweight methods, possibly because BART-base produces more fluent but less distinctive errors. Token probability classifier best C=10.0 on cross-validation indicating stronger regularization needed.</div>
    </div>
  </div>

  <!-- T5 PANEL -->
  <div class="model-panel" id="panel-t5">
    <div class="panel-hero" style="background:linear-gradient(135deg,#d1fae5,#a7f3d0)">
      <div class="panel-hero-icon" style="background:#10b981">T</div>
      <div>
        <div class="panel-hero-title">T5 - Text-to-Text Transfer Transformer</div>
        <div class="panel-hero-sub">t5-small, unified text-to-text framework, span-corruption pre-training</div>
        <div class="panel-hero-badges">
          <span class="hero-badge" style="color:#065f46">60M parameters</span>
          <span class="hero-badge" style="color:#065f46">Text-to-text</span>
          <span class="hero-badge" style="color:#065f46">Span corruption</span>
          <span class="hero-badge" style="color:#065f46">512 token context</span>
        </div>
      </div>
    </div>

    <div class="verdict-box" style="background:#f0fdf4;border-color:#10b981">
      <div class="verdict-title" style="color:#16a34a">Architecture overview</div>
      <div class="verdict-text" style="color:#14532d">T5 frames every NLP task as a text-to-text problem - the input is a text string and the output is a text string. Pre-trained using span corruption where random spans of input tokens are masked and the model learns to reconstruct them. T5-small is the lightest variant with 6 encoder and 6 decoder layers, hidden size 512, and only 60M parameters - making it the smallest model in this benchmark.</div>
    </div>

    <div class="section-grid">
      <div class="section-card">
        <div class="sc-label" style="color:#10b981"><div class="sc-label-dot" style="background:#10b981"></div>Summary generation</div>
        <div class="sc-title">How summaries were generated</div>
        <div class="sc-text">Same generation pipeline as BART. Beam search (num_beams=4) for deterministic summaries, K=10 samples with temperature=1.0 for SelfCheckGPT, greedy with output_scores=True for token log-probs. Truncation at max_length=512 (T5-small's context limit). T5 requires a task prefix - "summarize:" prepended to all inputs automatically by the tokenizer.</div>
        <div class="sc-tags">
          <span class="sc-tag">num_beams=4</span>
          <span class="sc-tag">K=10 samples</span>
          <span class="sc-tag">max_length=512</span>
          <span class="sc-tag">summarize: prefix</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#10b981"><div class="sc-label-dot" style="background:#10b981"></div>Datasets covered</div>
        <div class="sc-title">3 datasets, 4,360 total documents</div>
        <div class="sc-text">Same dataset splits as BART loaded from factshield-team/cache. CNN/DailyMail and XSum use the "article" column as input. FaithBench uses the "source" column (different schema). The splitter.py used separate make_splits and make_splits_from_dataset functions to handle FaithBench's different structure.</div>
        <div class="sc-tags">
          <span class="sc-tag">cnndm 1,400</span>
          <span class="sc-tag">xsum 1,400</span>
          <span class="sc-tag">faithbench 560</span>
          <span class="sc-tag">source column</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#ea580c"><div class="sc-label-dot" style="background:#ea580c"></div>Pipeline 1 - SelfCheckGPT</div>
        <div class="sc-title">Consistency scoring for T5 summaries</div>
        <div class="sc-text">T5-small generates shorter, more compact summaries than BART due to its smaller capacity. This affects the number of sentences per summary and therefore the number of scoring rows. The shorter summaries may have fewer sentences to compare across samples, which could affect the reliability of Ngram scoring. NLI scoring is less affected since it operates at sentence level.</div>
        <div class="sc-tags">
          <span class="sc-tag">BERTScore</span>
          <span class="sc-tag">NLI DeBERTa</span>
          <span class="sc-tag">Ngram n=1</span>
          <span class="sc-tag">compact summaries</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#2563eb"><div class="sc-label-dot" style="background:#2563eb"></div>Pipeline 2 - Entailment</div>
        <div class="sc-title">Source-grounded factual verification</div>
        <div class="sc-text">MiniCheck scores each T5 sentence against its source document. T5-small's limited capacity means it may produce more generic, extractive-style summaries that are easier to verify against the source. This is reflected in the relatively lower MiniCheck AUROC for T5 compared to PEGASUS, suggesting T5 hallucinations may be harder to detect via entailment.</div>
        <div class="sc-tags">
          <span class="sc-tag">MiniCheck</span>
          <span class="sc-tag">roberta-large</span>
          <span class="sc-tag">extractive tendency</span>
          <span class="sc-tag">10,080 rows</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#d97706"><div class="sc-label-dot" style="background:#d97706"></div>Pipeline 3 - Token probability</div>
        <div class="sc-title">Best performing pipeline for T5</div>
        <div class="sc-text">Token probability is the strongest detector for T5, achieving AUROC 0.5486 - the highest single result across all model-pipeline combinations. The max_entropy feature is most predictive (coefficient 1.336), suggesting T5-small shows clear uncertainty spikes at hallucinated tokens. This is consistent with the model being smaller and less confident when fabricating content.</div>
        <div class="sc-tags">
          <span class="sc-tag">AUROC 0.5486</span>
          <span class="sc-tag">max_entropy key</span>
          <span class="sc-tag">C=1.0 best</span>
          <span class="sc-tag">best overall</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Evaluation results</div>
        <div class="sc-title">T5 AUROC on FaithBench</div>
        <table class="score-table">
          <thead><tr><th>Method</th><th>AUROC</th><th>AUPRC</th></tr></thead>
          <tbody>
            <tr><td>SelfCheck NLI</td><td><span class="score-val" style="color:#ea580c">0.5528</span><div class="score-bar-wrap"><div class="score-bar" style="width:97%;background:#ea580c"></div></div></td><td>0.7142</td></tr>
            <tr><td>SelfCheck BERTScore</td><td><span class="score-val" style="color:#ea580c">0.4743</span><div class="score-bar-wrap"><div class="score-bar" style="width:84%;background:#ea580c"></div></div></td><td>0.6178</td></tr>
            <tr><td>MiniCheck</td><td><span class="score-val" style="color:#2563eb">0.4637</span><div class="score-bar-wrap"><div class="score-bar" style="width:82%;background:#2563eb"></div></div></td><td>0.6374</td></tr>
            <tr><td>Token probability</td><td><span class="score-val" style="color:#d97706">0.5486</span><div class="score-bar-wrap"><div class="score-bar" style="width:97%;background:#d97706"></div></div></td><td>0.7357</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card full" style="margin-bottom:14px">
      <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Validation steps</div>
      <div class="sc-title">End-to-end verification for T5</div>
      <ul class="step-list">
        <li><div class="step-num" style="background:#10b981">1</div><div>Cache generated on Kaggle T4 GPU. Initial attempt failed due to incorrect model ID ("google/t5-small" - correct is "t5-small"). After fix, 9 T5 configs pushed to Hub successfully. FaithBench required handling the "source" column (not "article" or "document").</div></li>
        <li><div class="step-num" style="background:#ea580c">2</div><div>SelfCheckGPT scoring completed for all 3 datasets. Empty-sample guard added after some T5 FaithBench summaries had empty primary outputs, causing IndexError in bert_score. Fixed by filtering samples before scoring.</div></li>
        <li><div class="step-num" style="background:#2563eb">3</div><div>MiniCheck entailment scoring completed. Results appended to task2_scores alongside BART and PEGASUS results using drop_duplicates on (doc_id, summarizer, dataset, method).</div></li>
        <li><div class="step-num" style="background:#d97706">4</div><div>Token probability classifier trained on T5 FaithBench split. Best C=1.0 via 5-fold cross-validation. AUROC 0.5486 is the highest single result in the entire benchmark. max_entropy is the most important feature.</div></li>
        <li><div class="step-num" style="background:#16a34a">5</div><div>All 9 T5 Hub configs verified by validate_all.py. 36/36 total checks passed across all models.</div></li>
      </ul>
    </div>

    <div class="verdict-box" style="background:#f0fdf4;border-color:#22c55e">
      <div class="verdict-title" style="color:#16a34a">Key finding - T5</div>
      <div class="verdict-text" style="color:#14532d">T5-small produces the most detectable hallucinations overall. Token probability achieves AUROC 0.5486 - the highest in the benchmark - suggesting that T5's limited capacity creates measurable uncertainty spikes at hallucinated tokens. SelfCheckGPT NLI also performs well at 0.5528. Interestingly MiniCheck is weakest for T5 (0.4637), suggesting T5 hallucinations may not contradict the source document directly but rather add unsupported details that are harder to catch via entailment. The combination of NLI and token probability covers different failure modes and would likely give the best combined detector.</div>
    </div>
  </div>

  <!-- PEGASUS PANEL -->
  <div class="model-panel" id="panel-pegasus">
    <div class="panel-hero" style="background:linear-gradient(135deg,#fef3c7,#fde68a)">
      <div class="panel-hero-icon" style="background:#f59e0b">P</div>
      <div>
        <div class="panel-hero-title">PEGASUS - Pre-training with Extracted Gap-sentences</div>
        <div class="panel-hero-sub">google/pegasus-large, gap-sentence generation pre-training, summarization-specific</div>
        <div class="panel-hero-badges">
          <span class="hero-badge" style="color:#92400e">568M parameters</span>
          <span class="hero-badge" style="color:#92400e">GSG pre-training</span>
          <span class="hero-badge" style="color:#92400e">Summarization-specific</span>
          <span class="hero-badge" style="color:#92400e">1024 token context</span>
        </div>
      </div>
    </div>

    <div class="verdict-box" style="background:#fffbeb;border-color:#f59e0b">
      <div class="verdict-title" style="color:#d97706">Architecture overview</div>
      <div class="verdict-text" style="color:#78350f">PEGASUS uses a novel pre-training objective called Gap Sentence Generation (GSG): important sentences are removed from documents and the model learns to generate them from the remaining context. This makes it specifically pre-trained for abstractive summarization, unlike BART and T5 which use general pre-training objectives. PEGASUS-large has 16 encoder and 16 decoder layers with hidden size 1024 - the largest model in this benchmark at 568M parameters.</div>
    </div>

    <div class="section-grid">
      <div class="section-card">
        <div class="sc-label" style="color:#f59e0b"><div class="sc-label-dot" style="background:#f59e0b"></div>Summary generation</div>
        <div class="sc-title">How summaries were generated</div>
        <div class="sc-text">Same generation pipeline but with reduced batch_size=4 due to PEGASUS-large's 2.3GB size requiring more GPU memory on Kaggle T4. K=5 stochastic samples (instead of K=10) for cnndm and xsum due to session time limits - faithbench used K=5 throughout. Despite the smaller K, PEGASUS shows the strongest SelfCheckGPT performance, suggesting its diverse sampling is more informative.</div>
        <div class="sc-tags">
          <span class="sc-tag">num_beams=4</span>
          <span class="sc-tag">K=5 samples</span>
          <span class="sc-tag">batch_size=4</span>
          <span class="sc-tag">2.3GB model</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#f59e0b"><div class="sc-label-dot" style="background:#f59e0b"></div>Datasets covered</div>
        <div class="sc-title">3 datasets, 4,360 total documents</div>
        <div class="sc-text">Same dataset splits as BART and T5. PEGASUS-large was run in a separate Kaggle notebook session due to memory requirements. The model loaded with several warnings about missing embed_positions weights and tied word embeddings - these are known for PEGASUS-large and do not affect generation quality.</div>
        <div class="sc-tags">
          <span class="sc-tag">cnndm 1,400</span>
          <span class="sc-tag">xsum 1,400</span>
          <span class="sc-tag">faithbench 560</span>
          <span class="sc-tag">separate session</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#ea580c"><div class="sc-label-dot" style="background:#ea580c"></div>Pipeline 1 - SelfCheckGPT</div>
        <div class="sc-title">Best NLI score in the benchmark</div>
        <div class="sc-text">PEGASUS achieves the highest SelfCheckGPT NLI score (AUROC 0.5653) - the best single result across all model-pipeline combinations. This is likely because PEGASUS generates more diverse stochastic samples due to its summarization-specific pre-training. When sampling with temperature=1.0, PEGASUS explores a wider range of phrasings, making inconsistencies in hallucinated content more detectable via NLI.</div>
        <div class="sc-tags">
          <span class="sc-tag">AUROC 0.5653</span>
          <span class="sc-tag">best overall</span>
          <span class="sc-tag">diverse samples</span>
          <span class="sc-tag">NLI strongest</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#2563eb"><div class="sc-label-dot" style="background:#2563eb"></div>Pipeline 2 - Entailment</div>
        <div class="sc-title">Best MiniCheck score across models</div>
        <div class="sc-text">MiniCheck achieves AUROC 0.5220 for PEGASUS - the highest entailment score across all three models. PEGASUS-large's summarization-specific training means it generates more abstractive, fluent summaries that include more genuine hallucinations (unsupported assertions) rather than just copying source sentences. These hallucinations are more detectable by MiniCheck which explicitly checks source grounding.</div>
        <div class="sc-tags">
          <span class="sc-tag">AUROC 0.5220</span>
          <span class="sc-tag">best entailment</span>
          <span class="sc-tag">abstractive</span>
          <span class="sc-tag">source-grounded check</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#d97706"><div class="sc-label-dot" style="background:#d97706"></div>Pipeline 3 - Token probability</div>
        <div class="sc-title">Weakest token probability result</div>
        <div class="sc-text">Token probability performs worst for PEGASUS (AUROC 0.4735). This is likely because PEGASUS-large, being a larger and summarization-specialized model, is more confident across the board - it assigns higher probabilities to the tokens it generates, including hallucinated ones. The model's specialization means it has learned to be confident when generating summary-style text, masking the uncertainty signals that indicate hallucination.</div>
        <div class="sc-tags">
          <span class="sc-tag">AUROC 0.4735</span>
          <span class="sc-tag">C=10.0 best</span>
          <span class="sc-tag">high confidence</span>
          <span class="sc-tag">masked uncertainty</span>
        </div>
      </div>
      <div class="section-card">
        <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Evaluation results</div>
        <div class="sc-title">PEGASUS AUROC on FaithBench</div>
        <table class="score-table">
          <thead><tr><th>Method</th><th>AUROC</th><th>AUPRC</th></tr></thead>
          <tbody>
            <tr><td>SelfCheck NLI</td><td><span class="score-val" style="color:#ea580c">0.5653</span><div class="score-bar-wrap"><div class="score-bar" style="width:100%;background:#ea580c"></div></div></td><td>0.7047</td></tr>
            <tr><td>SelfCheck BERTScore</td><td><span class="score-val" style="color:#ea580c">0.4670</span><div class="score-bar-wrap"><div class="score-bar" style="width:83%;background:#ea580c"></div></div></td><td>0.6523</td></tr>
            <tr><td>MiniCheck</td><td><span class="score-val" style="color:#2563eb">0.5220</span><div class="score-bar-wrap"><div class="score-bar" style="width:92%;background:#2563eb"></div></div></td><td>0.6698</td></tr>
            <tr><td>Token probability</td><td><span class="score-val" style="color:#d97706">0.4735</span><div class="score-bar-wrap"><div class="score-bar" style="width:84%;background:#d97706"></div></div></td><td>0.6826</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card full" style="margin-bottom:14px">
      <div class="sc-label" style="color:#16a34a"><div class="sc-label-dot" style="background:#16a34a"></div>Validation steps</div>
      <div class="sc-title">End-to-end verification for PEGASUS</div>
      <ul class="step-list">
        <li><div class="step-num" style="background:#f59e0b">1</div><div>Cache generated in a separate Kaggle session due to 2.3GB model size. Initial attempt used incorrect model ID ("pegasus-large" - correct is "google/pegasus-large"). After fix, batch_size reduced to 4 to avoid OOM. K=5 used instead of K=10 for cnndm and xsum.</div></li>
        <li><div class="step-num" style="background:#ea580c">2</div><div>SelfCheckGPT scoring ran with the same empty-sample guard as T5. PEGASUS achieved the highest NLI score (0.5653) across all models. Ngram scoring had fewer valid samples after inf filtering (n=90 for faithbench) making those results less reliable.</div></li>
        <li><div class="step-num" style="background:#2563eb">3</div><div>MiniCheck entailment scoring achieved AUROC 0.5220 - highest across all models. High ECE (0.6036) indicates MiniCheck probabilities are poorly calibrated for PEGASUS, assigning very low scores even for faithful sentences.</div></li>
        <li><div class="step-num" style="background:#d97706">4</div><div>Token probability classifier trained on PEGASUS FaithBench split. Best C=10.0 on cross-validation. Lowest AUROC of the three models (0.4735), consistent with PEGASUS being more confident at generation time.</div></li>
        <li><div class="step-num" style="background:#16a34a">5</div><div>All 9 PEGASUS Hub configs verified. validate_all.py confirmed presence and non-emptiness of pegasus_cnndm_summaries through pegasus_faithbench_token_scores. 36/36 total validation checks passed.</div></li>
      </ul>
    </div>

    <div class="verdict-box" style="background:#fffbeb;border-color:#f59e0b">
      <div class="verdict-title" style="color:#d97706">Key finding - PEGASUS</div>
      <div class="verdict-text" style="color:#78350f">PEGASUS is the most detectable model overall when using consistency-based methods. Its summarization-specific GSG pre-training leads to more abstractive, diverse outputs - both in beam-search summaries (more hallucination-prone) and stochastic samples (more diverse, making inconsistencies detectable). SelfCheckGPT NLI (0.5653) and MiniCheck (0.5220) are both at their best for PEGASUS. However token probability performs worst here because PEGASUS's specialization gives it high confidence even when hallucinating. The recommendation is to use SelfCheckGPT NLI for PEGASUS hallucination detection.</div>
    </div>
  </div>

</div>
"""
with gr.Blocks(title="FactShield", head=APP_HEAD_JS) as demo:
    gr.Markdown("# FactShield - Hallucination Detection Benchmark")
    gr.Markdown(
        "Comparing SelfCheckGPT, entailment verification, and token probability "
        "across BART, T5, PEGASUS on FaithBench."
    )

    with gr.Tabs():
        with gr.Tab("Pipeline architecture and docs"):
            gr.HTML(ARCHITECTURE_HTML)
            gr.Markdown("---")
            gr.HTML(DOCS_HTML)

        with gr.Tab("Model deep dives"):
            gr.HTML(MODELS_TAB_HTML)

        with gr.Tab("Results and evaluation"):
            refresh_btn = gr.Button("Load results from Hub", variant="primary")
            gr.Markdown(
                "Results load live from factshield-team/results on HuggingFace Hub."
            )
            results_out = gr.HTML(
                "<p style='font-family:sans-serif;color:#9ca3af;font-size:13px;padding:20px 0'>"
                "Click 'Load results from Hub' to fetch the latest evaluation results.</p>"
            )
            refresh_btn.click(fn=load_and_render_results, outputs=results_out)

demo.launch(theme=gr.themes.Soft())
