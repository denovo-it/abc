#!/usr/bin/env python3
"""
Patch per aggiungere la funzionalità di anteprima grafica a calibrate.py

Eseguire su Orange Pi:
    python3 patch_calibrate_display.py

Questo script modifica calibrate.py per aggiungere:
- Auto-detection dell'ambiente grafico
- Parametro --no-display per disabilitare l'anteprima
- Visualizzazione dell'anteprima con cv2.imshow() se disponibile
"""

import os
import sys
import re

CALIBRATE_FILE = '/home/orangepi/abc/software/ocr-test/calibrate.py'

# Codice da aggiungere dopo gli import
DISPLAY_UTILITIES = '''

# ============================================================================
# DISPLAY UTILITIES
# ============================================================================

def has_display():
    """Check if we're running in a graphical environment"""
    # Check for X11 display
    if os.environ.get('DISPLAY'):
        return True
    # Check for Wayland
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    # Check for macOS
    if sys.platform == 'darwin':
        return True
    # Check for Windows
    if sys.platform == 'win32':
        return True
    return False


def can_show_gui():
    """Check if OpenCV can show GUI windows"""
    if not has_display():
        return False
    try:
        backend = cv2.getBuildInformation()
        if 'GTK' in backend or 'QT' in backend or 'Win32' in backend or 'Cocoa' in backend:
            return True
        return True
    except:
        return False


def show_image(title, image, wait_key=True):
    """
    Show image in a window if possible.

    Returns:
        True if image was shown, False otherwise
    """
    try:
        cv2.imshow(title, image)
        if wait_key:
            print(f"\\n👁️  Showing preview window: '{title}'")
            print("   Press any key to continue...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return True
    except cv2.error as e:
        print(f"⚠️  Cannot show window: {e}")
        return False

'''


def patch_file():
    """Apply patch to calibrate.py"""

    if not os.path.exists(CALIBRATE_FILE):
        print(f"❌ File not found: {CALIBRATE_FILE}")
        sys.exit(1)

    # Backup
    backup_file = CALIBRATE_FILE + '.backup_before_display'
    with open(CALIBRATE_FILE, 'r') as f:
        original = f.read()

    with open(backup_file, 'w') as f:
        f.write(original)
    print(f"✅ Backup created: {backup_file}")

    content = original

    # 1. Update docstring
    old_doc = '''Usage: python3 calibrate.py [--debug]
"""'''
    new_doc = '''Usage: python3 calibrate.py [--debug] [--no-display]

Options:
    --debug        Save intermediate debug images
    --no-display   Never show preview window (use in headless mode)
"""'''

    if old_doc in content:
        content = content.replace(old_doc, new_doc)
        print("✅ Updated docstring")

    # 2. Add display utilities after imports
    import_marker = "import argparse"
    if import_marker in content and "def has_display():" not in content:
        content = content.replace(
            import_marker,
            import_marker + DISPLAY_UTILITIES
        )
        print("✅ Added display utilities")

    # 3. Update argparse to add --no-display
    old_argparse = """    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode (save intermediate images)"
    )

    args = parser.parse_args()"""

    new_argparse = """    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode (save intermediate images)"
    )
    parser.add_argument(
        '--no-display',
        action='store_true',
        help="Never show preview window (use in headless mode)"
    )

    args = parser.parse_args()

    # Determine if we should show GUI
    if args.no_display:
        args.show_gui = False
    else:
        args.show_gui = can_show_gui()
        if args.show_gui:
            print("🖥️  Graphical environment detected - will show preview window")"""

    if old_argparse in content:
        content = content.replace(old_argparse, new_argparse)
        print("✅ Updated argparse")

    # 4. Update calibrate_camera signature
    old_sig = "def calibrate_camera(rtsp_url, debug=False):"
    new_sig = "def calibrate_camera(rtsp_url, debug=False, show_gui=False):"
    if old_sig in content:
        content = content.replace(old_sig, new_sig)
        print("✅ Updated calibrate_camera signature")

    # 5. Update calibrate_camera call
    old_call = "rectangle = calibrate_camera(rtsp_url, debug=args.debug)"
    new_call = "rectangle = calibrate_camera(rtsp_url, debug=args.debug, show_gui=args.show_gui)"
    if old_call in content:
        content = content.replace(old_call, new_call)
        print("✅ Updated calibrate_camera call")

    # 6. Add GUI preview after saving preview image
    old_preview = '''    os.makedirs('test_images', exist_ok=True)
    preview_path = 'test_images/calibration_preview.jpg'
    cv2.imwrite(preview_path, preview)
    print(f"✅ Preview saved: {preview_path}")

    if debug:
        cv2.imwrite('debug_4_final.jpg', preview)

    return rectangle'''

    new_preview = '''    # Add text overlay with coordinates
    text = f"Area: ({x1},{y1}) - ({x2},{y2}) | {area_w}x{area_h}px"
    cv2.putText(preview, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2)

    os.makedirs('test_images', exist_ok=True)
    preview_path = 'test_images/calibration_preview.jpg'
    cv2.imwrite(preview_path, preview)
    print(f"✅ Preview saved: {preview_path}")

    if debug:
        cv2.imwrite('debug_4_final.jpg', preview)

    # Show GUI preview if available
    if show_gui:
        # Resize for display if too large
        display_img = preview.copy()
        max_display_h = 800
        if display_img.shape[0] > max_display_h:
            scale = max_display_h / display_img.shape[0]
            new_w = int(display_img.shape[1] * scale)
            display_img = cv2.resize(display_img, (new_w, max_display_h))

        show_image("Calibration Preview - Press any key to continue", display_img)

    return rectangle'''

    if old_preview in content:
        content = content.replace(old_preview, new_preview)
        print("✅ Added GUI preview code")

    # Write patched file
    with open(CALIBRATE_FILE, 'w') as f:
        f.write(content)

    print(f"\n✅ Patch applied successfully to {CALIBRATE_FILE}")
    print("\nUsage:")
    print("  python3 calibrate.py              # Auto-detect display, show if available")
    print("  python3 calibrate.py --no-display # Never show window (headless mode)")
    print("  python3 calibrate.py --debug      # Save debug images")


if __name__ == "__main__":
    patch_file()
