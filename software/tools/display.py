"""A.B.C. Pipeline - OpenCV display overlay module.

Provides visual overlays for the pipeline window:
- Detection rectangles (loading area, book, person)
- Hourglass animation during OCR scanning
- Result box with book information
- Countdown bar during WAITING state
- Status text
"""

import cv2
import math
import time
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOOK_CLASS_ID = 73
PERSON_CLASS_ID = 0

# Native screen resolution (Orange Pi 5 Plus HDMI)
SCREEN_W = 1024
SCREEN_H = 600

COLORS = {
    'loading_area': (0, 255, 0),       # green
    'book': (255, 180, 0),             # cyan/orange
    'person': (0, 0, 255),             # red
    'text_bg': (40, 40, 40),           # dark gray
    'bar_accept': (0, 200, 0),         # green
    'bar_reject': (0, 0, 220),         # red
    'bar_empty': (80, 80, 80),         # gray
    'status_watching': (0, 200, 255),  # yellow
    'status_scanning': (0, 165, 255),  # orange
    'status_waiting': (200, 200, 0),   # cyan
}

FONT = cv2.FONT_HERSHEY_SIMPLEX
AA = cv2.LINE_AA  # antialiasing for all text

WINDOW_NAME = "A.B.C."
_window_created = False
_logo_img = None  # cached logo image


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------

def _load_logo():
    """Load and cache the Denovo logo (with alpha channel)."""
    global _logo_img
    if _logo_img is not None:
        return _logo_img
    import os
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'doc', 'denovo-logo.png')
    if os.path.exists(logo_path):
        _logo_img = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    return _logo_img


def _overlay_logo(frame, logo, x, y):
    """Overlay RGBA logo onto frame at position (x, y)."""
    if logo is None:
        return
    lh, lw = logo.shape[:2]
    fh, fw = frame.shape[:2]
    # Clip to frame bounds
    if x + lw > fw:
        lw = fw - x
    if y + lh > fh:
        lh = fh - y
    if lw <= 0 or lh <= 0:
        return
    roi = frame[y:y + lh, x:x + lw]
    logo_crop = logo[:lh, :lw]
    if logo_crop.shape[2] == 4:
        alpha = logo_crop[:, :, 3:4] / 255.0
        bgr = logo_crop[:, :, :3]
        frame[y:y + lh, x:x + lw] = (bgr * alpha + roi * (1 - alpha)).astype(np.uint8)
    else:
        frame[y:y + lh, x:x + lw] = logo_crop


def init_window():
    """Create fullscreen display window (once)."""
    global _window_created
    if _window_created:
        return
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)
    _window_created = True
    _load_logo()  # preload logo


def draw_logo_small(frame):
    """Draw small Denovo logo in top-right corner."""
    logo = _load_logo()
    if logo is None:
        return
    # Resize for top-right corner
    lh, lw = logo.shape[:2]
    target_h = 160
    scale = target_h / lh
    small = cv2.resize(logo, (int(lw * scale), target_h),
                       interpolation=cv2.INTER_AREA)
    fh, fw = frame.shape[:2]
    x = fw - small.shape[1] - 8
    y = 8
    _overlay_logo(frame, small, x, y)


def show(frame):
    """Display frame and process GUI events."""
    cv2.imshow(WINDOW_NAME, frame)
    cv2.waitKey(1)


def destroy():
    """Clean up window."""
    global _window_created
    cv2.destroyAllWindows()
    _window_created = False


# ---------------------------------------------------------------------------
# Detection overlays
# ---------------------------------------------------------------------------

def draw_detections(frame, detections, loading_area):
    """Draw detection rectangles with labels and confidence.

    detections: list of dicts with 'class_id', 'score', 'box', 'in_area'.
    Detections outside loading area are drawn dimmed/dashed.
    """
    # Loading area rectangle
    if loading_area:
        lx1, ly1, lx2, ly2 = loading_area
        cv2.rectangle(frame, (lx1, ly1), (lx2, ly2),
                      COLORS['loading_area'], 1)
        cv2.putText(frame, "Loading Area", (lx1, ly1 - 5),
                    FONT, 0.5, COLORS['loading_area'], 1, AA)

    for det in detections:
        cid = det['class_id']
        score = det['score']
        in_area = det.get('in_area', True)
        x1, y1, x2, y2 = [int(v) for v in det['box']]

        if cid == BOOK_CLASS_ID:
            color = COLORS['book']
            label = f"Book {score*100:.0f}%"
        elif cid == PERSON_CLASS_ID:
            color = COLORS['person']
            label = f"Person {score*100:.0f}%"
        else:
            continue

        if not in_area:
            # Dim color for out-of-area detections
            color = tuple(c // 3 for c in color)
            label += " [out]"

        thickness = 2 if in_area else 1
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        # Label background
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.6, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1),
                      color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    FONT, 0.6, (0, 0, 0), 1, AA)


# ---------------------------------------------------------------------------
# Hourglass (scanning animation)
# ---------------------------------------------------------------------------

def draw_hourglass(frame, tick=0, progress=None, phase_text=None):
    """Draw rotating hourglass at center of frame with progress percentage.

    progress: 0.0-1.0 (None = no percentage shown)
    phase_text: optional text like "OCR Pass 1/2" shown below percentage
    """
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    size = 60

    # Semi-transparent dark circle
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), size + 20, (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Two triangles forming hourglass, rotated by tick
    angle = (tick * 15) % 360
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def _rotate(pts):
        centered = pts.astype(np.float64) - [cx, cy]
        rotated = np.zeros_like(centered)
        rotated[:, 0] = centered[:, 0] * cos_a - centered[:, 1] * sin_a
        rotated[:, 1] = centered[:, 0] * sin_a + centered[:, 1] * cos_a
        return (rotated + [cx, cy]).astype(np.int32)

    top_pts = np.array([
        [cx - size // 2, cy - size // 2],
        [cx + size // 2, cy - size // 2],
        [cx, cy],
    ], dtype=np.int32)

    bot_pts = np.array([
        [cx - size // 2, cy + size // 2],
        [cx + size // 2, cy + size // 2],
        [cx, cy],
    ], dtype=np.int32)

    top_rot = _rotate(top_pts)
    bot_rot = _rotate(bot_pts)

    cv2.fillPoly(frame, [top_rot], (200, 200, 100), AA)
    cv2.fillPoly(frame, [bot_rot], (100, 200, 200), AA)
    cv2.polylines(frame, [top_rot], True, (255, 255, 255), 2, AA)
    cv2.polylines(frame, [bot_rot], True, (255, 255, 255), 2, AA)

    # Progress percentage inside hourglass
    if progress is not None:
        pct = max(0, min(100, int(progress * 100)))
        pct_text = f"{pct}%"
        (pw, ph), _ = cv2.getTextSize(pct_text, FONT, 0.9, 2)
        cv2.putText(frame, pct_text, (cx - pw // 2, cy + ph // 2),
                    FONT, 0.9, (255, 255, 255), 2, AA)

    # Phase text below hourglass (green on dark background)
    if phase_text:
        y_label = cy + size + 50
        font_scale = 0.7
        thickness = 2
        (ptw, pth), baseline = cv2.getTextSize(phase_text, FONT, font_scale, thickness)
        pad = 10
        tx = cx - ptw // 2
        # Dark background rectangle
        overlay = frame.copy()
        cv2.rectangle(overlay,
                      (tx - pad, y_label - pth - pad),
                      (tx + ptw + pad, y_label + baseline + pad),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, phase_text, (tx, y_label),
                    FONT, font_scale, (0, 220, 0), thickness, AA)


# ---------------------------------------------------------------------------
# Result box
# ---------------------------------------------------------------------------

def draw_result_box(frame, title, author, publisher):
    """Draw large semi-transparent result box at top center of frame."""
    h, w = frame.shape[:2]

    lines = []
    if title and title != '[not identified]':
        lines.append(("Title:", title))
    if author and author != '[not identified]':
        lines.append(("Author:", author))
    if publisher and publisher != '[not identified]':
        lines.append(("Publisher:", publisher))

    if not lines:
        return

    label_scale = 0.7
    value_scale = 0.9
    thickness = 2
    padding = 20
    line_height = 45

    # Measure widths
    max_tw = 0
    for label, value in lines:
        (lw, _), _ = cv2.getTextSize(label, FONT, label_scale, 1)
        (vw, _), _ = cv2.getTextSize(value, FONT, value_scale, thickness)
        max_tw = max(max_tw, lw + 10 + vw)

    box_w = max_tw + padding * 2
    box_h = len(lines) * line_height + padding * 2
    box_x = (w - box_w) // 2
    box_y = 10

    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x, box_y),
                  (box_x + box_w, box_y + box_h),
                  COLORS['text_bg'], -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    # Border
    cv2.rectangle(frame, (box_x, box_y),
                  (box_x + box_w, box_y + box_h),
                  (200, 200, 200), 1)

    # Text lines: label in gray, value in white/large
    for i, (label, value) in enumerate(lines):
        y = box_y + padding + (i + 1) * line_height - 8
        (lw, _), _ = cv2.getTextSize(label, FONT, label_scale, 1)
        cv2.putText(frame, label, (box_x + padding, y),
                    FONT, label_scale, (150, 150, 150), 1, AA)
        cv2.putText(frame, value, (box_x + padding + lw + 10, y),
                    FONT, value_scale, (255, 255, 255), thickness, AA)


# ---------------------------------------------------------------------------
# Countdown bar
# ---------------------------------------------------------------------------

def draw_countdown_bar(frame, remaining_ratio, mode='reject'):
    """Draw horizontal countdown bar at bottom of frame.

    remaining_ratio: 1.0 (full) -> 0.0 (empty)
    mode: 'reject' (red bar) or 'accept' (green bar)
    """
    h, w = frame.shape[:2]
    bar_h = 60
    bar_y = h - bar_h

    # Empty bar background
    cv2.rectangle(frame, (0, bar_y), (w, h), COLORS['bar_empty'], -1)

    # Filled portion
    fill_w = int(w * max(0.0, min(1.0, remaining_ratio)))
    if fill_w > 0:
        color = COLORS['bar_accept'] if mode == 'accept' else COLORS['bar_reject']
        cv2.rectangle(frame, (0, bar_y), (fill_w, h), color, -1)

    # Text
    if mode == 'reject':
        text = "Person detected - REJECTING"
    else:
        text = "Book removed - accepting..."

    (tw, th), _ = cv2.getTextSize(text, FONT, 0.6, 1)
    tx = (w - tw) // 2
    ty = bar_y + (bar_h + th) // 2
    cv2.putText(frame, text, (tx, ty),
                FONT, 0.6, (255, 255, 255), 1, AA)


# ---------------------------------------------------------------------------
# Splash / loading screen
# ---------------------------------------------------------------------------

def draw_splash(status_text, steps=None):
    """Draw splash/loading screen with A.B.C. title and loading status.

    steps: list of (label, done_bool) tuples for progress checklist.
    """
    frame = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
    h, w = frame.shape[:2]

    # Centered logo at top
    logo = _load_logo()
    if logo is not None:
        lh, lw = logo.shape[:2]
        # Resize to ~100px height for splash
        target_h = 100
        scale = target_h / lh
        splash_logo = cv2.resize(logo, (int(lw * scale), target_h),
                                 interpolation=cv2.INTER_AREA)
        lx = (w - splash_logo.shape[1]) // 2
        ly = 20
        _overlay_logo(frame, splash_logo, lx, ly)

    # Title (below logo)
    title = "A.B.C."
    (tw, th), _ = cv2.getTextSize(title, FONT, 1.5, 2)
    title_y = 190 if logo is not None else h // 3
    cv2.putText(frame, title, ((w - tw) // 2, title_y),
                FONT, 1.5, (200, 200, 200), 2, AA)

    # Subtitle
    sub = "AI Book Cataloguer"
    (sw, sh), _ = cv2.getTextSize(sub, FONT, 0.7, 1)
    sub_y = title_y + 35
    cv2.putText(frame, sub, ((w - sw) // 2, sub_y),
                FONT, 0.7, (120, 120, 120), 1, AA)

    # URL
    url = "https://denovo.srl"
    (uw, uh), _ = cv2.getTextSize(url, FONT, 0.5, 1)
    url_y = sub_y + 28
    cv2.putText(frame, url, ((w - uw) // 2, url_y),
                FONT, 0.5, (80, 80, 80), 1, AA)

    # Step checklist
    if steps:
        y_start = url_y + 45
        for i, (label, done) in enumerate(steps):
            y = y_start + i * 28
            if done:
                mark = "[OK]"
                color = (0, 200, 0)
            else:
                mark = "[..]"
                color = (100, 100, 100)
            cv2.putText(frame, f"  {mark} {label}", (w // 2 - 140, y),
                        FONT, 0.55, color, 1, AA)

    # Current status at bottom (with animated dots)
    # Animated dots only for loading messages (not for final status like 'Ready!')
    if status_text.endswith('..') or status_text.endswith('...'):
        n_dots = int(time.time() * 2) % 4
        display_text = status_text.rstrip('.') + '.' * max(1, n_dots)
    else:
        display_text = status_text
    (tw2, th2), _ = cv2.getTextSize(display_text, FONT, 0.7, 2)
    cv2.putText(frame, display_text, ((w - tw2) // 2, h - 60),
                FONT, 0.7, (0, 165, 255), 2, AA)

    show(frame)


# ---------------------------------------------------------------------------
# Hint text (bottom of frame)
# ---------------------------------------------------------------------------

def draw_hint(frame, text):
    """Draw hint text centered at bottom of frame."""
    h, w = frame.shape[:2]
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.5, 1)
    tx = (w - tw) // 2
    ty = h - 10
    # Dark background for readability
    cv2.rectangle(frame, (tx - 5, ty - th - 5), (tx + tw + 5, ty + 5),
                  (0, 0, 0), -1)
    cv2.putText(frame, text, (tx, ty),
                FONT, 0.5, (150, 150, 150), 1, AA)


# ---------------------------------------------------------------------------
# Status text
# ---------------------------------------------------------------------------

def draw_status(frame, text, color=None):
    """Draw status text at top-left corner with dark background, logo top-right."""
    if color is None:
        color = (255, 255, 255)

    (tw, th), _ = cv2.getTextSize(text, FONT, 0.8, 2)
    cv2.rectangle(frame, (5, 5), (15 + tw, 15 + th), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, 10 + th),
                FONT, 0.8, color, 2, AA)


# ---------------------------------------------------------------------------
# Frame on canvas (aspect-ratio-preserving fit)
# ---------------------------------------------------------------------------

def frame_on_canvas(crop):
    """Place crop on a black 1024x600 canvas, preserving aspect ratio, centered."""
    canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
    ch, cw = crop.shape[:2]
    if ch == 0 or cw == 0:
        return canvas
    scale = min(SCREEN_W / cw, SCREEN_H / ch)
    new_w = int(cw * scale)
    new_h = int(ch * scale)
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    x_off = (SCREEN_W - new_w) // 2
    y_off = (SCREEN_H - new_h) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


# ---------------------------------------------------------------------------
# Diagnostics overlay
# ---------------------------------------------------------------------------

def draw_diag_overlay(frame, lines):
    """Draw semi-transparent diagnostics panel at bottom-left of the frame.

    lines: iterable of strings (most recent last).
    """
    if not lines:
        return
    h, w = frame.shape[:2]
    font_scale = 1.0
    line_h = 32
    max_lines = min(len(lines), 5)
    panel_h = max_lines * line_h + 28
    panel_w = 700
    panel_y = h - panel_h

    # Semi-transparent dark background
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, panel_y), (panel_w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Draw last N lines, bottom-aligned
    visible = list(lines)[-max_lines:]
    y = panel_y + line_h
    for line in visible:
        cv2.putText(frame, line[:60], (8, y), FONT, font_scale,
                    (0, 220, 0), 1, AA)
        y += line_h


# ---------------------------------------------------------------------------
# Shutdown countdown overlay
# ---------------------------------------------------------------------------

def draw_shutdown_countdown(frame, remaining_secs):
    """Draw large centered shutdown countdown on frame."""
    h, w = frame.shape[:2]
    # Dark overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    text = f"SHUTDOWN in {remaining_secs}s"
    (tw, th), _ = cv2.getTextSize(text, FONT, 1.5, 3)
    cv2.putText(frame, text, ((w - tw) // 2, (h + th) // 2),
                FONT, 1.5, (0, 0, 255), 3, AA)

    hint = "Show CANCEL QR to abort"
    (hw, hh), _ = cv2.getTextSize(hint, FONT, 0.7, 1)
    cv2.putText(frame, hint, ((w - hw) // 2, (h + th) // 2 + 50),
                FONT, 0.7, (200, 200, 200), 1, AA)


# ---------------------------------------------------------------------------
# Accept / Reject fullscreen feedback
# ---------------------------------------------------------------------------

def show_accepted(duration=1.5):
    """Show a large green checkmark fullscreen."""
    frame = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
    cx, cy = SCREEN_W // 2, SCREEN_H // 2
    # Draw a thick checkmark (V shape)
    s = 140  # half-size
    pts = np.array([
        [cx - s, cy],
        [cx - s // 3, cy + s * 2 // 3],
        [cx + s, cy - s * 2 // 3],
    ], dtype=np.int32)
    cv2.polylines(frame, [pts], False, (0, 220, 0), 28, AA)
    show(frame)
    time.sleep(duration)


def show_rejected(duration=1.5):
    """Show a large red X fullscreen."""
    frame = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
    cx, cy = SCREEN_W // 2, SCREEN_H // 2
    s = 120  # half-size
    cv2.line(frame, (cx - s, cy - s), (cx + s, cy + s), (0, 0, 220), 28, AA)
    cv2.line(frame, (cx + s, cy - s), (cx - s, cy + s), (0, 0, 220), 28, AA)
    show(frame)
    time.sleep(duration)
