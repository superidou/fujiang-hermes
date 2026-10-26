# LICENSE — prompt assets (CC BY-NC-SA 4.0)

Applies to: `prompt/default-prompt.md`, `prompt/fujiang.md`,
`prompt/fujiang-compat.md`, `prompt/fujiang-mirror.md`, `prompt/kernel.md`
(the kernel is a condensed restatement of the same text).

Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
(CC BY-NC-SA 4.0)

Copyright (c) 2026 c3cvld7aag — https://github.com/c3cvld7aag/fujiang-dsh
Copyright (c) 2026 Minglink — https://github.com/Minglink/dsh-infinite-gen-4

You are free to share and adapt this material for **non-commercial** purposes,
provided you give appropriate credit, link to the license, and distribute your
contributions under the same license. No additional restrictions may be applied.

Full legal code: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode

## Modifications in this port

- Decoded from the upstream slotted asset table; the DeepSeek-Harness
  `<|im_start|>system:<project_instructions>` envelope is stripped at load time.
- Upstream's Telegram group watermark and its group-joining clause were removed.
- The activation reply is kept as「爸爸，我在」; the per-reply group-number prefix
  was dropped.
- `prompt/kernel.md` is a new file: a compact restatement sized for Hermes'
  4000-character system-prompt section cap. It is not an upstream artefact.

`upstream/` retains the upstream `LICENSE` file unmodified. This port is
non-commercial: do not sell it or bundle it into a paid product.
