# ============================================================
# Genetic Markov Generator
# Periodic Embedding + Simulation Selection
# ============================================================

import os
import random
import math
from collections import defaultdict, Counter
from janome.tokenizer import Tokenizer

# -----------------------------
# 設定
# -----------------------------
TARGET_DIR = r"C:\Users\kmrno\Desktop\output"
ENCODING = "utf-8"

GRAM = 8
OUTPUT_LENGTH = 1000
SIM_LENGTH = 500
SIM_ROUNDS = 5

PHASE_PERIOD = 97.0
LATENT_PROB = 0.5

THEME_TEXT = "黄泉の死神の手招きが見える"
THEME_GAIN = 7.0
DOMINANT_GAIN = 8.5

# 周期埋め込み
CYCLE_LENGTHS = [3, 7, 13]

tokenizer = Tokenizer()

# -----------------------------
# 基本
# -----------------------------
def load_texts(directory):
    out = []
    for f in os.listdir(directory):
        p = os.path.join(directory, f)
        if os.path.isfile(p):
            with open(p, encoding=ENCODING) as fh:
                out.append(fh.read())
    return out

def tokenize(text):
    return [t.surface for t in tokenizer.tokenize(text)]

# -----------------------------
# 周期埋め込みトークン
# -----------------------------
def make_core_tokens(text):
    n = len(text)
    tokens = []
    periods = [1] + CYCLE_LENGTHS

    for i in range(n):
        base = text[i]
        embedding = []

        for s, p in enumerate(periods):
            pos = s % p
            embedding.append(ord(text[(i + pos) % n]))

        tokens.append((base, tuple(embedding)))

    return tokens

# -----------------------------
# 語彙
# -----------------------------
def build_vocab(core_tokens):
    uniq = list(set(core_tokens))
    vocab = {t:i for i,t in enumerate(uniq)}
    ivocab = {i:t for t,i in vocab.items()}
    return vocab, ivocab

# -----------------------------
# Markov
# -----------------------------
def build_markov(seq, vocab):
    chain = defaultdict(Counter)

    for i in range(len(seq) - GRAM):
        st = tuple(vocab[seq[i+j]] for j in range(GRAM))
        nx = vocab[seq[i+GRAM]]
        chain[st][nx] += 1

    return chain

# -----------------------------
# 位相
# -----------------------------
def build_phases(vocab_size):
    return {
        tid: math.sin(2 * math.pi * (tid % PHASE_PERIOD) / PHASE_PERIOD)
        for tid in range(vocab_size)
    }

# -----------------------------
# 遺伝子（2系統）
# -----------------------------
def build_genes(vocab_size):
    genes = {}
    for tid in range(vocab_size):
        g = f"g{tid}_{random.randrange(9999)}"
        genes[tid] = {"self": g, "dom": g}
    return genes

# -----------------------------
# テーマ遺伝子
# -----------------------------
def seed_theme_genes(vocab, ivocab, theme_tokens, genes):
    theme_set = set()
    for tid, tok in ivocab.items():
        if tok[0] in theme_tokens:
            theme_set.add(genes[tid]["self"])
    return theme_set

# -----------------------------
# 遺伝勝負
# -----------------------------
def genetic_battle(a, b, freq, phase, genes):
    score_a = freq + phase
    score_b = freq

    if score_a >= score_b:
        if random.random() < 0.6:
            genes[b]["dom"] = genes[a]["dom"]
        elif random.random() < LATENT_PROB:
            genes[b]["dom"] = genes[a]["self"]

# -----------------------------
# シミュレーション生成
# -----------------------------
def simulate(chain, genes, phases, theme_gene_set):
    st = random.choice(list(chain.keys()))
    used = Counter()

    for _ in range(SIM_LENGTH):
        cand = chain.get(st)
        if not cand:
            st = random.choice(list(chain.keys()))
            continue

        cur = st[-1]
        weighted = []

        for nx,f in cand.items():
            genetic_battle(cur, nx, f, phases[nx], genes)
            w = f
            if genes[nx]["dom"] in theme_gene_set:
                w *= THEME_GAIN
            weighted.append((nx, w))

        total = sum(w for _,w in weighted)
        r = random.uniform(0, total)
        acc = 0

        for nx,w in weighted:
            acc += w
            if acc >= r:
                used[genes[nx]["dom"]] += 1
                st = st[1:] + (nx,)
                break

    return used

# -----------------------------
# 淘汰加速
# -----------------------------
def accelerate_selection(genes, sim_stats):
    if not sim_stats:
        return

    threshold = sum(sim_stats.values()) / len(sim_stats)

    for tid,g in genes.items():
        if sim_stats.get(g["dom"], 0) < threshold:
            if random.random() < 0.5:
                g["dom"] = g["self"]

# -----------------------------
# 本生成
# -----------------------------
def generate(chain, genes, ivocab, phases, theme_gene_set):
    # シミュレーション先行
    for _ in range(SIM_ROUNDS):
        stats = simulate(chain, genes, phases, theme_gene_set)
        accelerate_selection(genes, stats)

    # 実生成
    st = random.choice(list(chain.keys()))
    out = [ivocab[i][0] for i in st]

    for _ in range(OUTPUT_LENGTH):
        cand = chain.get(st)
        if not cand:
            st = random.choice(list(chain.keys()))
            continue

        cur = st[-1]
        weighted = []

        for nx,f in cand.items():
            w = f
            if genes[nx]["dom"] in theme_gene_set:
                w *= THEME_GAIN
            weighted.append((nx, w))

        total = sum(w for _,w in weighted)
        r = random.uniform(0, total)
        acc = 0

        for nx,w in weighted:
            acc += w
            if acc >= r:
                out.append(ivocab[nx][0])
                st = st[1:] + (nx,)
                break

    return "".join(out)

# ============================================================
# 実行
# ============================================================
if __name__ == "__main__":
    texts = load_texts(TARGET_DIR)

    core_seq = []
    for t in texts:
        core_seq.extend(make_core_tokens(t))

    vocab, ivocab = build_vocab(core_seq)
    chain = build_markov(core_seq, vocab)

    phases = build_phases(len(vocab))
    genes = build_genes(len(vocab))

    theme_tokens = tokenize(THEME_TEXT)
    theme_gene_set = seed_theme_genes(vocab, ivocab, theme_tokens, genes)

    print(generate(chain, genes, ivocab, phases, theme_gene_set))
