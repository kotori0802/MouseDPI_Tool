"""Windows Raw Input helper: hidden window, JSON-line MovementSample source.

Brand-neutral class name. Emits one JSON object per line:
  {"type":"delta","dx":...,"dy":...,"device":"...","time_perf":...}
  {"type":"status","message":"..."}

Graceful shutdown (UI-1B.3A):
  Parent writes ``stop\\n`` to stdin → helper posts WM_CLOSE → message loop exits
  → stdout flushes/closes → parent reader reaches EOF.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import sys
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
RIM_TYPEMOUSE = 0
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100
RIDEV_REMOVE = 0x00000001

# 64-bit-safe message types. wintypes.LPARAM/WPARAM can be 32-bit on some
# Python builds and overflow when DefWindowProcW is invoked (causes lag/faults).
LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

_hwnd_box: list[int] = []
_hwnd_lock = threading.Lock()


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wt.USHORT),
        ("usUsage", wt.USHORT),
        ("dwFlags", wt.DWORD),
        ("hwndTarget", wt.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wt.DWORD),
        ("dwSize", wt.DWORD),
        ("hDevice", wt.HANDLE),
        ("wParam", wt.WPARAM),
    ]


class RAWMOUSE_UNION(ctypes.Union):
    _fields_ = [
        ("ulButtons", wt.ULONG),
        ("usButtonFlags", wt.USHORT),
        ("usButtonData", wt.USHORT),
    ]


class RAWMOUSE(ctypes.Structure):
    _anonymous_ = ("buttons",)
    _fields_ = [
        ("usFlags", wt.USHORT),
        ("buttons", RAWMOUSE_UNION),
        ("ulRawButtons", wt.ULONG),
        ("lLastX", wt.LONG),
        ("lLastY", wt.LONG),
        ("ulExtraInformation", wt.ULONG),
    ]


class RAWINPUT_DATA(ctypes.Union):
    _fields_ = [("mouse", RAWMOUSE)]


class RAWINPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", RAWINPUT_DATA),
    ]


WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, WPARAM, LPARAM)
HICON = getattr(wt, "HICON", ctypes.c_void_p)
HCURSOR = getattr(wt, "HCURSOR", ctypes.c_void_p)
HBRUSH = getattr(wt, "HBRUSH", ctypes.c_void_p)
HINSTANCE = getattr(wt, "HINSTANCE", ctypes.c_void_p)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROCTYPE),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def get_raw_input(lparam):
    size = wt.UINT(0)
    user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
    if size.value == 0:
        return None
    buf = ctypes.create_string_buffer(size.value)
    read = user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
    if read != size.value:
        return None
    return ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents


def _unregister_raw_input(hwnd) -> None:
    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01
    rid.usUsage = 0x02
    rid.dwFlags = RIDEV_REMOVE
    rid.hwndTarget = hwnd
    try:
        user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE))
    except Exception:
        pass


def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_INPUT:
        raw = get_raw_input(lparam)
        if raw and raw.header.dwType == RIM_TYPEMOUSE:
            dx = int(raw.mouse.lLastX)
            dy = int(raw.mouse.lLastY)
            if dx or dy:
                emit(
                    {
                        "type": "delta",
                        "dx": dx,
                        "dy": dy,
                        "device": str(int(raw.header.hDevice or 0)),
                        "time_perf": time.perf_counter(),
                    }
                )
        return 0
    if msg == WM_CLOSE:
        _unregister_raw_input(hwnd)
        user32.DestroyWindow(hwnd)
        return 0
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def _request_quit() -> None:
    with _hwnd_lock:
        hwnd = _hwnd_box[0] if _hwnd_box else None
    if hwnd:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def _stdin_watcher() -> None:
    """Listen for parent graceful-stop command on stdin."""
    try:
        for raw in sys.stdin:
            cmd = (raw or "").strip().lower()
            if cmd in {"stop", "quit", "exit"}:
                emit({"type": "status", "message": "raw_input_delta_bridge_stop_requested"})
                _request_quit()
                return
    except Exception:
        # stdin closed / unavailable — parent will terminate/kill as fallback.
        return


def main() -> int:
    user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, WPARAM, LPARAM]
    user32.DefWindowProcW.restype = LRESULT

    hinst = kernel32.GetModuleHandleW(None)
    class_name = "MouseDpiToolRawInputDeltaBridge"
    wndproc = WNDPROCTYPE(wnd_proc)

    wc = WNDCLASS()
    wc.lpfnWndProc = wndproc
    wc.hInstance = hinst
    wc.lpszClassName = class_name

    atom = user32.RegisterClassW(ctypes.byref(wc))
    if not atom:
        emit({"type": "status", "message": "RegisterClassW failed"})
        return 1

    hwnd = user32.CreateWindowExW(
        0, class_name, class_name, 0, 0, 0, 0, 0, None, None, hinst, None
    )
    if not hwnd:
        emit({"type": "status", "message": "CreateWindowExW failed"})
        return 2

    with _hwnd_lock:
        _hwnd_box.clear()
        _hwnd_box.append(int(hwnd))

    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01
    rid.usUsage = 0x02
    rid.dwFlags = RIDEV_INPUTSINK
    rid.hwndTarget = hwnd

    ok = user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE))
    if not ok:
        emit({"type": "status", "message": "RegisterRawInputDevices failed"})
        return 3

    watcher = threading.Thread(target=_stdin_watcher, name="raw-input-stdin-stop", daemon=True)
    watcher.start()

    emit({"type": "status", "message": "raw_input_delta_bridge_started"})

    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    emit({"type": "status", "message": "raw_input_delta_bridge_stopped"})
    with _hwnd_lock:
        _hwnd_box.clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
