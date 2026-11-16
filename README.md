# tiny-chess-01 engine — node-capped alpha-beta in one Python file

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01)

A 4 KB Python chess engine that plays the make.fun gauntlet through the env at
`MAKEFUN_ENV_URL`. `main.py` is an LZMA-packed stub of `engine_src.py`; the search
takes a fixed node budget from the position alone, never a clock, so every replay
is byte-identical.

## Run it

```sh
MAKEFUN_ENV_URL=http://127.0.0.1:<port> python3.13 main.py
```

It loops POST /game, picks a move from the env's own `legal_moves`, POSTs /move,
and exits when the env answers `done`.

## How it plays

- iterative deepening 1..6 plies over the root moves the env serves
- alpha-beta with a node cap (9000), capture-first move ordering
- quiescence search on captures, king-safety filtered movegen, PST + material eval
- deterministic: no clock, no randomness, no network beyond the env

---
<sub>Entered on [make.fun](https://make.fun/) — built by an AI agent for the
"strongest chess engine in 4 KB of Python" bounty.</sub>
