# Reuse the same X11 connection from various other modules.
from Xlib import display
dpy = display.Display()

def get_active_window():
    return dpy.get_input_focus().focus


_no_net_wm_name = False

def window_title(w):
    global _no_net_wm_name

    if not _no_net_wm_name:
        title = w.get_full_text_property(dpy.get_atom("_NET_WM_NAME"))
        if title is not None:
            return title

    title = w.get_full_text_property(dpy.get_atom("WM_NAME"))
    if title is not None:
        _no_net_wm_name = True

    return title



