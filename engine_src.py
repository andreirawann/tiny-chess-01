# tiny-chess-01 engine source (MIT). `makefun compress` turns this into main.py.
# Plays the gauntlet through the env at MAKEFUN_ENV_URL. The search never reads a
# clock: a fixed node budget comes from the position alone, so a replay is
# byte-identical. Root moves are the env's own legal_moves list; deeper plies are
# generated here (pseudo-legal, filtered by king safety).
import json
import os
import urllib.request

U = os.environ["MAKEFUN_ENV_URL"]
VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 0}
FILES = "abcdefgh"
NSTEP = (-17, -15, -10, -6, 6, 10, 15, 17)
KSTEP = (-9, -8, -7, -1, 1, 7, 8, 9)
DIAG = (-9, -7, 7, 9)
ORTH = (-8, -1, 1, 8)
PST = {
    "p": (0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, -20, -20, 10, 10, 5, 5, -5, -10, 0, 0, -10, -5, 5,
          0, 0, 0, 20, 20, 0, 0, 0, 5, 5, 5, 10, 10, 5, 5, 5, 10, 10, 10, 20, 20, 10, 10, 10,
          20, 20, 20, 30, 30, 20, 20, 20, 0, 0, 0, 0, 0, 0, 0, 0),
    "n": (-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 5, 5, 0, -20, -40, -30, 5, 10, 15,
          15, 10, 5, -30, -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30, -30, 0,
          10, 15, 15, 10, 0, -30, -40, -20, 0, 0, 0, 0, -20, -40, -50, -40, -30, -30, -30, -30,
          -40, -50),
    "b": (-20, -10, -10, -10, -10, -10, -10, -20, -10, 5, 0, 0, 0, 0, 5, -10, -10, 10, 10, 10, 10,
          10, 10, -10, -10, 0, 10, 10, 10, 10, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10, -10, 0, 5, 10,
          10, 5, 0, -10, -10, 0, 0, 0, 0, 0, 0, -10, -20, -10, -10, -10, -10, -10, -10, -20),
    "r": (0, 0, 0, 5, 5, 0, 0, 0, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0,
          0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 5, 10, 10, 10, 10, 10,
          10, 5, 0, 0, 0, 0, 0, 0, 0, 0),
    "q": (-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 5, 0, 0, 0, 0, -10, -10, 5, 5, 5, 5, 5, 0,
          -10, 0, 0, 5, 5, 5, 5, 0, -5, -5, 0, 5, 5, 5, 5, 0, -5, -10, 0, 5, 5, 5, 5, 0, -10, -10,
          0, 0, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20),
    "k": (20, 30, 10, 0, 0, 10, 30, 20, 20, 20, 0, 0, 0, 0, 20, 20, -10, -20, -20, -20, -20, -20,
          -20, -10, -20, -30, -30, -40, -40, -30, -30, -20, -30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40,
          -40, -50, -50, -40, -40, -30),
}


def post(path, body):
    req = urllib.request.Request(U + path, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=9) as r:
        return json.load(r)


def parse(fen):
    """FEN -> (board, side, castling, ep). Board holds 64 chars, '.' empty."""
    p = fen.split()
    b = ["."] * 64
    rank, file = 7, 0
    for ch in p[0]:
        if ch == "/":
            rank, file = rank - 1, 0
        elif ch.isdigit():
            file += int(ch)
        else:
            b[rank * 8 + file] = ch
            file += 1
    ep = -1
    if len(p) > 3 and p[3] != "-":
        ep = (int(p[3][1]) - 1) * 8 + FILES.index(p[3][0])
    return b, p[1], p[2] if len(p) > 2 else "-", ep


def attacked(b, sq, by_white):
    """Does any piece of `by_white` attack square sq?"""
    f0, r0 = sq % 8, sq // 8
    pw = "P" if by_white else "p"
    dr = -1 if by_white else 1
    for f in (f0 - 1, f0 + 1):
        r = r0 + dr
        if 0 <= f < 8 and 0 <= r < 8 and b[r * 8 + f] == pw:
            return True
    n = "N" if by_white else "n"
    for d in NSTEP:
        t = sq + d
        if 0 <= t < 64 and abs(t % 8 - f0) <= 2 and b[t] == n:
            return True
    k = "K" if by_white else "k"
    for d in KSTEP:
        t = sq + d
        if 0 <= t < 64 and abs(t % 8 - f0) <= 1 and b[t] == k:
            return True
    q = "Q" if by_white else "q"
    for dirs, kinds in ((DIAG, ("B" if by_white else "b",)), (ORTH, ("R" if by_white else "r",))):
        for d in dirs:
            t = sq
            while True:
                f = t % 8
                t += d
                if not 0 <= t < 64 or abs(t % 8 - f) > 1:
                    break
                ch = b[t]
                if ch != ".":
                    if ch in kinds or ch == q:
                        return True
                    break
    return False


def king_sq(b, side):
    k = "K" if side == "w" else "k"
    return b.index(k) if k in b else -1


def gen(b, side, castling, ep):
    """Pseudo-legal moves for `side`: (from, to, promo)."""
    out = []
    white = side == "w"
    up = 8 if white else -8
    for i, p in enumerate(b):
        if p == "." or p.isupper() != white:
            continue
        t = p.lower()
        f, r = i % 8, i // 8
        if t == "p":
            to = i + up
            if 0 <= to < 64 and b[to] == ".":
                if r + (1 if white else -1) in (0, 7):
                    out += [(i, to, q) for q in "qrbn"]
                else:
                    out.append((i, to, ""))
                    if r == (1 if white else 6) and b[i + 2 * up] == ".":
                        out.append((i, i + 2 * up, ""))
            for d in (-1, 1):
                if not 0 <= f + d < 8:
                    continue
                to = i + up + d
                if not 0 <= to < 64:
                    continue
                q = b[to]
                if q != "." and q.isupper() != white:
                    if r + (1 if white else -1) in (0, 7):
                        out += [(i, to, pr) for pr in "qrbn"]
                    else:
                        out.append((i, to, ""))
                elif to == ep:
                    out.append((i, to, ""))
        elif t == "n":
            for d in NSTEP:
                to = i + d
                if 0 <= to < 64 and abs(to % 8 - f) <= 2:
                    q = b[to]
                    if q == "." or q.isupper() != white:
                        out.append((i, to, ""))
        elif t == "k":
            for d in KSTEP:
                to = i + d
                if 0 <= to < 64 and abs(to % 8 - f) <= 1:
                    q = b[to]
                    if q == "." or q.isupper() != white:
                        out.append((i, to, ""))
        else:
            dirs = DIAG if t == "b" else ORTH if t == "r" else DIAG + ORTH
            for d in dirs:
                to = i
                while True:
                    ff = to % 8
                    to += d
                    if not 0 <= to < 64 or abs(to % 8 - ff) > 1:
                        break
                    q = b[to]
                    if q == ".":
                        out.append((i, to, ""))
                        continue
                    if q.isupper() != white:
                        out.append((i, to, ""))
                    break
    if castling != "-":
        base = 0 if white else 56
        rook = "R" if white else "r"
        if ("K" if white else "k") in castling and b[base + 5] == "." and b[base + 6] == ".":
            if b[base + 7] == rook and not attacked(b, base + 4, not white) \
                    and not attacked(b, base + 5, not white) and not attacked(b, base + 6, not white):
                out.append((base + 4, base + 6, ""))
        if ("Q" if white else "q") in castling and b[base] == rook and b[base + 1] == "." \
                and b[base + 2] == "." and b[base + 3] == "." and not attacked(b, base + 4, not white) \
                and not attacked(b, base + 3, not white) and not attacked(b, base + 2, not white):
            out.append((base + 4, base + 2, ""))
    return out


def make(b, side, castling, ep, m):
    """Apply move m; returns the new board, side, castling rights and ep square."""
    nb = list(b)
    f, t, pr = m
    piece = nb[f]
    capture = nb[t]
    nb[t] = (pr.upper() if side == "w" else pr) if pr else piece
    nb[f] = "."
    if piece.lower() == "p" and t == ep and capture == "." and abs(t - f) in (7, 9):
        nb[t - 8 if side == "w" else t + 8] = "."
    if piece.lower() == "k" and abs(t - f) == 2:
        if t > f:
            nb[t - 1], nb[t + 1] = nb[t + 1], "."
        else:
            nb[t + 1], nb[t - 2] = nb[t - 2], "."
    cast = castling
    if piece.lower() == "k":
        cast = cast.replace("K" if side == "w" else "k", "").replace("Q" if side == "w" else "q", "")
    for sq, flag in ((f, "QK"), (t, "QK")):
        if sq in (0, 56):
            cast = cast.replace("Q", "") if sq == 0 else cast.replace("k", "")
        if sq in (7, 63):
            cast = cast.replace("K", "") if sq == 7 else cast.replace("q", "")
    new_ep = -1
    if piece.lower() == "p" and abs(t - f) == 16:
        new_ep = (f + t) // 2
    return nb, ("b" if side == "w" else "w"), cast or "-", new_ep


def legal_moves(b, side, castling, ep):
    out = []
    for m in gen(b, side, castling, ep):
        nb, ns, nc, ne = make(b, side, castling, ep, m)
        k = king_sq(nb, side)
        if k < 0 or not attacked(nb, k, side == "b"):
            out.append(m)
    return out


def evaluate(b):
    s = 0
    for i, p in enumerate(b):
        if p == ".":
            continue
        v = VAL[p.lower()] + PST[p.lower()][i if p.isupper() else 63 - i]
        s += v if p.isupper() else -v
    return s


def quiesce(b, side, castling, ep, alpha, beta, box):
    box[0] += 1
    if box[0] > box[1]:
        return alpha
    stand = evaluate(b) * (1 if side == "w" else -1)
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand
    caps = [m for m in legal_moves(b, side, castling, ep)
            if b[m[1]] != "." or m[2] or (m[1] == ep and m[1] >= 0)]
    caps.sort(key=lambda m: -VAL.get(b[m[1]].lower(), 0) if b[m[1]] != "." else -100)
    for m in caps:
        nb, ns, nc, ne = make(b, side, castling, ep, m)
        v = -quiesce(nb, ns, nc, ne, -beta, -alpha, box)
        if box[0] > box[1]:
            return alpha
        if v >= beta:
            return beta
        if v > alpha:
            alpha = v
    return alpha


def negamax(b, side, castling, ep, depth, alpha, beta, box, ply):
    box[0] += 1
    if box[0] > box[1]:
        return alpha
    if depth <= 0:
        return quiesce(b, side, castling, ep, alpha, beta, box)
    ms = legal_moves(b, side, castling, ep)
    if not ms:
        k = king_sq(b, side)
        return -30000 + ply if k >= 0 and attacked(b, k, side == "b") else 0
    ms.sort(key=lambda m: -VAL.get(b[m[1]].lower(), 0))
    for m in ms:
        nb, ns, nc, ne = make(b, side, castling, ep, m)
        v = -negamax(nb, ns, nc, ne, depth - 1, -beta, -alpha, box, ply + 1)
        if box[0] > box[1]:
            return alpha
        if v >= beta:
            return beta
        if v > alpha:
            alpha = v
    return alpha


def choose(fen, legal, budget):
    """Best of the env's legal root moves, by a node-capped iterative deepening."""
    b, side, castling, ep = parse(fen)
    roots = []
    for s in legal:
        f = (int(s[1]) - 1) * 8 + FILES.index(s[0])
        t = (int(s[3]) - 1) * 8 + FILES.index(s[2])
        roots.append((f, t, s[4:]))
    if not roots:
        return None
    best = roots[0]
    for depth in (1, 2, 3, 4, 5, 6):
        scored = []
        box = [0, budget]
        for m in roots:
            nb, ns, nc, ne = make(b, side, castling, ep, m)
            v = -negamax(nb, ns, nc, ne, depth - 1, -30000, 30000, box, 1)
            scored.append((v, m))
            if box[0] > budget:
                break
        if scored:
            scored.sort(key=lambda x: (-x[0], x[1]))
            best = scored[0][1]
        if box[0] > budget:
            break
    return FILES[best[0] % 8] + str(best[0] // 8 + 1) + FILES[best[1] % 8] + str(best[1] // 8 + 1) + best[2]


def main():
    while True:
        g = post("/game", {})
        while g.get("status") == "your_move":
            move = choose(g["fen"], g["legal_moves"], 9000)
            g = post("/move", {"game": g["game"], "move": move})
        if g.get("status") == "done":
            return 0


raise SystemExit(main())
