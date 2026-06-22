# Task 21 Evidence — Wave 4-T4: mode/chapter/autonomy selector + full ChatRequest

## Commit
`00ed268d0c47e44f97fa36115a0665bf6c758fb7`

## Changes
- `novel-frontend/src/app/projects/[id]/agent/page.tsx`: Added toolbar row with mode selector, chapter picker, and autonomy preset dropdown; updated `handleSend` to pass full `ChatRequest`.

## Verification

### Automated
```bash
cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npm run lint
# ✓ clean (no output = pass)

cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npm run build
# ✓ Compiled successfully in 2.1s
# ✓ TypeScript clean
# ✓ Static pages generated (8/8)

cd /home/sihan/文档/Projects/AI-Novel-Generation && .venv/bin/python -m pytest tests/ -q --tb=no
# 220 passed
```

### Line Count
```bash
wc -l novel-frontend/src/app/projects/[id]/agent/page.tsx
# 194 lines (≤200 requirement met)
```

### Git Status
```bash
git status --short
# M  .omo/plans/agent-and-project-optimization.md
# M  novel-frontend/src/app/projects/[id]/agent/page.tsx
```

## Implementation Details

### Mode Selector
- Select component with values: `auto` (自动), `brainstorm` (脑暴), `writing` (写作)
- Default: `auto`
- When explicit (`brainstorm` or `writing`), backend skips `_detect_intent`

### Chapter Picker
- Select populated from `useChapters(projectId)`
- Disabled when `mode === "brainstorm"` or no chapters exist
- Shows "（暂无章节）" placeholder when empty
- Only sends `chapter_outline_id` in `writing` mode

### Autonomy Preset Dropdown
- DropdownMenu with three sections:
  1. **写作模式**: suggest (建议) / draft (草稿) / direct (直接) — radio group
  2. **重写轮数**: range slider 1-5, default 3
  3. **粒度**: chapter (章) / volume (卷) / act (幕) — radio group
- Default: draft / 3 / chapter

### ChatRequest
`handleSend` now passes:
```ts
{
  message: input.trim(),
  chapter_outline_id: mode === "writing" ? chapterId : null,
  target_words: 3000,
  mode: mode === "auto" ? null : mode,
  autonomy_config: {
    write_mode: writeMode,
    max_rewrite_rounds: maxRewriteRounds,
    milestone_granularity: milestoneGranularity,
  },
}
```

### Constraints Met
- ✓ Used existing shadcn `Select` from `@/components/ui/select`
- ✓ Did NOT add react-markdown (todo 4-T6)
- ✓ Did NOT add suggestion card wiring (todo 4-T5)
- ✓ Did NOT touch backend files
- ✓ Page ≤200 lines (194 lines)
- ✓ `npm run lint && npm run build` + `pytest tests/ -q --tb=no` green
