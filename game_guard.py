"""Read-only Windows foreground and notification-state avoidance."""
import ctypes
from ctypes import wintypes
import os
import psutil

GAME_NAMES = frozenset(('overwatch.exe', 'overwatch', 'cs2.exe', 'valorant-win64-shipping.exe',
    'league of legends.exe', 'dota2.exe', 'r5apex.exe', 'tslgame.exe'))
FOCUS_APPS = frozenset(('wemeetapp.exe', 'zoom.exe', 'ms-teams.exe', 'teams.exe', 'obs64.exe'))
SHELL_CLASSES = frozenset(('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'))


def is_game_process(name):
    return name.lower() in GAME_NAMES


def covers_monitor(client, monitor, tolerance=2):
    return all(abs(a - b) <= tolerance for a, b in zip(client, monitor))


def avoidance_reason(state=5, name='', window_class='', client=None, monitor=None,
                     own_window=False, extra_apps=''):
    # APP (7) means a Store app, not necessarily an interruption-sensitive scene.
    if state in (1, 2, 3, 4, 6):
        return {1: '锁屏或屏幕保护', 2: '全屏或演示', 3: '全屏游戏',
                4: '演示模式', 6: '系统安静时段'}[state]
    if own_window or window_class in SHELL_CLASSES:
        return ''
    custom = {part.strip().lower() for part in extra_apps.replace('；', ';').split(';') if part.strip()}
    if is_game_process(name) or name.lower() in FOCUS_APPS or name.lower() in custom:
        return '应用避让'
    if client and monitor and covers_monitor(client, monitor):
        return '全屏窗口'
    return ''


class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]


def current_avoidance_reason(extra_apps=''):
    if os.name != 'nt':
        return ''
    user = ctypes.windll.user32
    state = ctypes.c_int(5)
    try:
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
            state.value = 5
    except (OSError, AttributeError):
        pass
    reason = avoidance_reason(state.value)
    if reason:
        return reason
    try:
        user.GetForegroundWindow.restype = wintypes.HWND
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user.MonitorFromWindow.restype = wintypes.HANDLE
        user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
        hwnd = user.GetForegroundWindow()
        if not hwnd:
            return ''
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        cls = ctypes.create_unicode_buffer(256)
        user.GetClassNameW(hwnd, cls, 256)
        if pid.value == os.getpid() or cls.value in SHELL_CLASSES:
            return ''
        try:
            name = psutil.Process(pid.value).name()
        except psutil.Error:
            name = ''
        rect, point = wintypes.RECT(), wintypes.POINT()
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        client = monitor = None
        if (user.GetClientRect(hwnd, ctypes.byref(rect)) and
            user.ClientToScreen(hwnd, ctypes.byref(point)) and
            user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info))):
            client = (point.x, point.y, point.x + rect.right, point.y + rect.bottom)
            r = info.rcMonitor
            monitor = (r.left, r.top, r.right, r.bottom)
        return avoidance_reason(name=name, window_class=cls.value, client=client,
                                monitor=monitor, extra_apps=extra_apps)
    except (OSError, AttributeError):
        return ''


# Compatibility for existing probes; now covers all supported scenes.
def overwatch_foreground():
    return bool(current_avoidance_reason())
