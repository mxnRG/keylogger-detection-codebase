#!/bin/bash
# Test script for keyboard notifier module

echo "=========================================="
echo "FYP Keyboard Observer - Test Script"
echo "=========================================="
echo ""

# Check if module is loaded
if lsmod | grep -q fyp_kbd; then
    echo "[✓] Module fyp_kbd is loaded"
else
    echo "[✗] Module fyp_kbd is NOT loaded"
    echo "    Run: sudo insmod fyp_kbd.ko"
    exit 1
fi

echo ""
echo "IMPORTANT: Keyboard notifier catches TTY/console events best."
echo "To test effectively, switch to a virtual terminal:"
echo ""
echo "  1. Press Ctrl+Alt+F3 to switch to TTY3"
echo "  2. Login with your credentials"
echo "  3. Type a few keys (e.g., 'hello test')"
echo "  4. Press Ctrl+Alt+F2 to return to GUI"
echo "  5. Run: make logs"
echo ""
echo "Alternatively, test with this terminal (may have limited capture):"
echo "Type some text now, then press Enter to check logs..."
read -p "> " input

echo ""
echo "=========================================="
echo "Kernel Logs (last 30 lines):"
echo "=========================================="
sudo dmesg | grep "\[FYP\]" | tail -30

echo ""
echo "=========================================="
echo "Statistics:"
echo "=========================================="
EVENT_COUNT=$(sudo dmesg | grep -c "KEY_EVENT")
echo "Total KEY_EVENT logs captured: $EVENT_COUNT"

if [ $EVENT_COUNT -eq 0 ]; then
    echo ""
    echo "[!] No keyboard events captured yet."
    echo "    This is expected for GUI terminals (X11/Wayland)."
    echo "    Try switching to a TTY console (Ctrl+Alt+F3)."
fi

echo ""
