# UX Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** Fix all identified UX issues across the application: toast notifications, loading indicators, error handling, responsive layout, and display bugs.

**Architecture:** Add a shared toast component in base.html, HTMX event handlers for loading states, and targeted template fixes per module.

---

### Task 1: Toast Notification System

Add a global toast notification component in base.html that can be triggered via HTMX events or JavaScript. All CRUD operations will trigger a toast on success/failure.

**Files:** `app/templates/base.html`

**Changes:**
- Add toast HTML container (fixed bottom-right)
- Add CSS for toast animations
- Add JS function `showToast(message, type)` where type is "success" | "error" | "info"
- Add HTMX event listeners: `htmx:afterRequest` to auto-show toasts for certain endpoints

---

### Task 2: HTMX Loading Indicators

Add visual loading feedback to all HTMX operations.

**Files:** `app/templates/base.html`

**Changes:**
- Add `.htmx-request` styling for buttons (disabled + spinner)
- Add global CSS for loading states
- Configure `hx-indicator` on key interactive elements

---

### Task 3: Form Submission & Error Feedback

**Files:** All `_form.html` templates + modal close logic

**Changes:**
- Create a unified HTMX response handler that shows toast on success and keeps modal open on error
- Fix all CRUD endpoints to return proper success signals
- Add event handler: after successful form submit, close modal + show toast

---

### Task 4: Review JSON Rendering Fix

**Files:** `app/templates/review/_detail.html`, `app/routers/reviews.py`

**Changes:**
- Parse `findings` and `summary` JSON strings in the router before passing to template
- Display findings as formatted cards instead of raw JSON

---

### Task 5: Responsive Writer & Brainstorm Layout

**Files:** `app/templates/writer/index.html`, `app/templates/brainstorm/index.html`

**Changes:**
- Add CSS media queries: on small screens collapse sidebar into a toggleable overlay
- Add hamburger/toggle button for sidebar visibility
- Ensure content area fills remaining space

---

### Task 6: Outline "+子" Context

**Files:** `app/templates/outline/_form.html`

**Changes:**
- Pass parent item title to the modal
- Show "在 XXX 下添加子项" in modal title

---

### Task 7: Brainstorm Auto-scroll on Load

**Files:** `app/templates/brainstorm/_input.html`, `app/templates/brainstorm/index.html`

**Changes:**
- On page load, if sessionStorage has messages, scroll to bottom
- On history load, scroll to bottom

---

### Task 8: Network Error Handling

**Files:** `app/templates/base.html`

**Changes:**
- Add global `htmx:beforeOnLoad` or `htmx:responseError` handler to show toast on network errors
- Add per-endpoint fallback UI for critical partials
