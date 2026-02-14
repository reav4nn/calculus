#!/usr/bin/env python3

import sys
import os
import math
import re
from datetime import datetime

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, GObject, Pango

APP_ID = "io.github.calculus"


class Engine:
    safe_names = {
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "sqrt": math.sqrt, "log": math.log10, "ln": math.log,
        "pi": math.pi, "e": math.e, "abs": abs, "pow": pow,
    }

    def calc(self, expr):
        try:
            s = expr.replace("\u00d7", "*").replace("\u00f7", "/").replace("^", "**")
            s = s.replace("\u03c0", str(math.pi)).replace("\u221a", "sqrt")
            s = re.sub(r"(\d+\.?\d*)%", r"(\1/100)", s)

            code = compile(s, "<calc>", "eval")
            for name in code.co_names:
                if name not in self.safe_names:
                    raise NameError(name)

            r = eval(code, {"__builtins__": {}}, self.safe_names)

            if isinstance(r, float) and r == int(r) and abs(r) < 1e15:
                return str(int(r))
            return f"{r:.10g}" if isinstance(r, float) else str(r)
        except ZeroDivisionError:
            return "undefined"
        except Exception:
            return "error"


class HistoryRow(Gtk.Box):
    def __init__(self, expr, result, timestamp, on_click):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add_css_class("history-row")
        for prop in ("start", "end"):
            getattr(self, f"set_margin_{prop}")(8)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl = Gtk.Label(label=expr, xalign=0, hexpand=True)
        lbl.add_css_class("history-expr")
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        ts = Gtk.Label(label=timestamp)
        ts.add_css_class("history-time")
        top.append(lbl)
        top.append(ts)

        res = Gtk.Label(label=f"= {result}", xalign=0)
        res.add_css_class("history-result")

        self.append(top)
        self.append(res)

        gesture = Gtk.GestureClick()
        gesture.connect("released", lambda *_: on_click(result))
        self.add_controller(gesture)


class CalcButton(Gtk.Button):
    def __init__(self, label, classes=None):
        super().__init__(label=label)
        self.add_css_class("calc-btn")
        self.set_hexpand(True)
        self.set_vexpand(True)
        for c in (classes or []):
            self.add_css_class(c)


class CalculatorWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Calculus")
        self.set_default_size(420, 640)
        self.set_size_request(360, 540)

        self.engine = Engine()
        self.history = []
        self.current = ""
        self.last_result = ""
        self.fresh = True

        self._build()
        self._keys()

    def _build(self):
        self.split = Adw.OverlaySplitView()
        self.split.set_collapsed(True)
        self.split.set_pin_sidebar(False)
        self.split.set_max_sidebar_width(280)
        self.split.set_min_sidebar_width(240)
        self.split.set_sidebar_position(Gtk.PackType.START)

        # sidebar
        sidebar_hdr = Adw.HeaderBar()
        sidebar_hdr.set_show_end_title_buttons(False)
        sidebar_hdr.set_show_start_title_buttons(False)
        sidebar_hdr.add_css_class("flat")
        sidebar_hdr.set_title_widget(Adw.WindowTitle(title="History"))

        trash = Gtk.Button(icon_name="user-trash-symbolic")
        trash.add_css_class("flat")
        trash.set_tooltip_text("Clear history")
        trash.connect("clicked", self._clear_history)
        sidebar_hdr.pack_end(trash)

        scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.hist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.hist_box.add_css_class("history-list")
        scroller.set_child(self.hist_box)

        self.empty_page = Adw.StatusPage(
            title="No history yet",
            icon_name="document-open-recent-symbolic",
            description="Calculations will show up here",
        )
        self.empty_page.add_css_class("compact")

        self.hist_stack = Gtk.Stack()
        self.hist_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.hist_stack.set_transition_duration(200)
        self.hist_stack.add_named(self.empty_page, "empty")
        self.hist_stack.add_named(scroller, "list")
        self.hist_stack.set_visible_child_name("empty")

        sidebar_view = Adw.ToolbarView()
        sidebar_view.add_css_class("history-panel")
        sidebar_view.add_top_bar(sidebar_hdr)
        sidebar_view.set_content(self.hist_stack)
        self.split.set_sidebar(sidebar_view)

        # main content
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        header.set_title_widget(Adw.WindowTitle(title="Calculus"))

        hist_btn = Gtk.ToggleButton(icon_name="document-open-recent-symbolic")
        hist_btn.set_tooltip_text("History (Ctrl+H)")
        hist_btn.add_css_class("flat")
        hist_btn.bind_property(
            "active", self.split, "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        header.pack_start(hist_btn)

        theme_btn = Gtk.Button(icon_name="weather-clear-symbolic")
        theme_btn.set_tooltip_text("Toggle dark/light mode")
        theme_btn.add_css_class("flat")
        theme_btn.connect("clicked", self._toggle_theme)
        self._theme_btn = theme_btn
        header.pack_end(theme_btn)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.add_css_class("flat")
        menu = Gio.Menu()
        menu.append("Keyboard shortcuts", "app.shortcuts")
        menu.append("About", "app.about")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)

        main.append(header)

        # display
        display = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        display.add_css_class("display-box")
        display.set_margin_start(16)
        display.set_margin_end(16)
        display.set_margin_top(8)
        display.set_margin_bottom(8)

        self.expr_lbl = Gtk.Label(label="", xalign=1)
        self.expr_lbl.add_css_class("display-expr")
        self.expr_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.expr_lbl.set_selectable(True)

        self.result_lbl = Gtk.Label(label="0", xalign=1)
        self.result_lbl.add_css_class("display-result")
        self.result_lbl.set_selectable(True)

        display.append(self.expr_lbl)
        display.append(self.result_lbl)
        main.append(display)

        # buttons
        grid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        grid.add_css_class("button-grid")
        grid.set_vexpand(True)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_bottom(8)

        layout = [
            [("C", ["destructive"]), ("(", ["op"]), (")", ["op"]), ("\u00f7", ["op"])],
            [("7", []), ("8", []), ("9", []), ("\u00d7", ["op"])],
            [("4", []), ("5", []), ("6", []), ("\u2212", ["op"])],
            [("1", []), ("2", []), ("3", []), ("+", ["op"])],
            [("\u00b1", ["special"]), ("0", []), (".", []), ("=", ["accent"])],
            [("%", ["special"]), ("^", ["special"]), ("\u221a", ["special"]), ("\u232b", ["special"])],
        ]

        for items in layout:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.set_homogeneous(True)
            row.set_vexpand(True)
            row.set_margin_top(3)
            row.set_margin_bottom(3)
            for label, cls in items:
                btn = CalcButton(label, cls)
                btn.connect("clicked", self._btn_click, label)
                row.append(btn)
            grid.append(row)

        main.append(grid)
        self.split.set_content(main)
        self.set_content(self.split)

    def _keys(self):
        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._key_press)
        self.add_controller(ctrl)

    def _key_press(self, _ctrl, keyval, _code, state):
        is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)

        mapping = {
            Gdk.KEY_0: "0", Gdk.KEY_1: "1", Gdk.KEY_2: "2", Gdk.KEY_3: "3",
            Gdk.KEY_4: "4", Gdk.KEY_5: "5", Gdk.KEY_6: "6", Gdk.KEY_7: "7",
            Gdk.KEY_8: "8", Gdk.KEY_9: "9",
            Gdk.KEY_KP_0: "0", Gdk.KEY_KP_1: "1", Gdk.KEY_KP_2: "2",
            Gdk.KEY_KP_3: "3", Gdk.KEY_KP_4: "4", Gdk.KEY_KP_5: "5",
            Gdk.KEY_KP_6: "6", Gdk.KEY_KP_7: "7", Gdk.KEY_KP_8: "8",
            Gdk.KEY_KP_9: "9",
            Gdk.KEY_plus: "+", Gdk.KEY_KP_Add: "+",
            Gdk.KEY_minus: "\u2212", Gdk.KEY_KP_Subtract: "\u2212",
            Gdk.KEY_asterisk: "\u00d7", Gdk.KEY_KP_Multiply: "\u00d7",
            Gdk.KEY_slash: "\u00f7", Gdk.KEY_KP_Divide: "\u00f7",
            Gdk.KEY_period: ".", Gdk.KEY_KP_Decimal: ".", Gdk.KEY_comma: ".",
            Gdk.KEY_percent: "%",
            Gdk.KEY_parenleft: "(", Gdk.KEY_parenright: ")",
            Gdk.KEY_asciicircum: "^",
        }

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_equal):
            self._eval()
            return True
        if keyval == Gdk.KEY_BackSpace:
            self._backspace()
            return True
        if keyval in (Gdk.KEY_Escape, Gdk.KEY_Delete):
            self._clear()
            return True
        if is_ctrl and keyval == Gdk.KEY_h:
            self.split.set_show_sidebar(not self.split.get_show_sidebar())
            return True
        if keyval in mapping:
            self._input(mapping[keyval])
            return True
        return False

    def _btn_click(self, _btn, label):
        if label == "C":
            self._clear()
        elif label == "=":
            self._eval()
        elif label == "\u232b":
            self._backspace()
        elif label == "\u00b1":
            self._negate()
        elif label == "\u221a":
            self._input("\u221a(")
        else:
            self._input(label)

    def _input(self, ch):
        ops = {"+", "\u2212", "\u00d7", "\u00f7", "^"}

        if self.fresh and ch not in ops and ch not in (".", "(", ")", "%", "\u221a("):
            self.current = ""
            self.fresh = False

        if ch in ops and self.current and self.current[-1] in "+-\u00d7\u00f7^*/":
            self.current = self.current[:-1]

        self.current += ch
        self._refresh_display()
        self._preview()

    def _clear(self):
        self.current = ""
        self.last_result = ""
        self.fresh = True
        self.expr_lbl.set_label("")
        self.result_lbl.set_label("0")
        self.result_lbl.remove_css_class("err")

    def _backspace(self):
        if not self.current:
            return
        self.current = self.current[:-1]
        self._refresh_display()
        if self.current:
            self._preview()
        else:
            self.result_lbl.set_label("0")

    def _negate(self):
        if not self.current:
            return
        if self.current[0] in ("\u2212", "-"):
            self.current = self.current[1:]
        else:
            self.current = "\u2212" + self.current
        self._refresh_display()
        self._preview()

    def _eval(self):
        if not self.current:
            return

        raw = self.current.replace("\u2212", "-")
        result = self.engine.calc(raw)

        self.expr_lbl.set_label(self.current + " =")

        if result in ("error", "undefined"):
            self.result_lbl.set_label(result)
            self.result_lbl.add_css_class("err")
        else:
            self.result_lbl.set_label(result)
            self.result_lbl.remove_css_class("err")
            self.last_result = result
            self.current = result

            ts = datetime.now().strftime("%H:%M")
            self.history.append((raw.replace("-", "\u2212"), result, ts))
            self._push_history(raw.replace("-", "\u2212"), result, ts)

        self.fresh = True

        # subtle feedback
        self.result_lbl.add_css_class("result-pop")
        GLib.timeout_add(300, lambda: self.result_lbl.remove_css_class("result-pop"))

    def _preview(self):
        if not self.current:
            return
        r = self.engine.calc(self.current.replace("\u2212", "-"))
        if r not in ("error", "undefined"):
            self.expr_lbl.set_label(f"\u27f6 {r}")

    def _refresh_display(self):
        self.result_lbl.set_label(self.current or "0")
        self.result_lbl.remove_css_class("err")

    def _push_history(self, expr, result, ts):
        row = HistoryRow(expr, result, ts, self._reuse)
        self.hist_box.prepend(row)
        self.hist_stack.set_visible_child_name("list")

    def _reuse(self, val):
        self.current = val
        self.fresh = False
        self._refresh_display()
        self.split.set_show_sidebar(False)

    def _toggle_theme(self, _btn):
        sm = Adw.StyleManager.get_default()
        dark = sm.get_dark()

        content = self.get_content()
        content.set_opacity(0.0)

        if dark:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._theme_btn.set_icon_name("weather-clear-night-symbolic")
        else:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._theme_btn.set_icon_name("weather-clear-symbolic")

        self._fade_val = 0.0
        def _step():
            self._fade_val = min(self._fade_val + 0.08, 1.0)
            content.set_opacity(self._fade_val)
            if self._fade_val >= 1.0:
                return False
            return True
        GLib.timeout_add(12, _step)

    def _clear_history(self, _btn):
        while (child := self.hist_box.get_first_child()):
            self.hist_box.remove(child)
        self.history.clear()
        self.hist_stack.set_visible_child_name("empty")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._activate)

        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", self._about)
        self.add_action(about)

        shortcuts = Gio.SimpleAction.new("shortcuts", None)
        shortcuts.connect("activate", self._shortcuts)
        self.add_action(shortcuts)

    def _activate(self, app):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
        self._css()
        CalculatorWindow(app).present()

    def _css(self):
        provider = Gtk.CssProvider()
        provider.load_from_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _about(self, *_):
        Adw.AboutDialog(
            application_name="Calculus",
            application_icon="accessories-calculator",
            developer_name="reav4nn",
            version="1.0.0",
            license_type=Gtk.License.GPL_3_0,
            developers=["reav4nn"],
            copyright="\u00a9 2026",
            comments="a gtk4 calculator",
        ).present(self.get_active_window())

    def _shortcuts(self, *_):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)

        section = Gtk.ShortcutsSection(section_name="main", title="Shortcuts")
        section.set_visible(True)

        group = Gtk.ShortcutsGroup(title="General")
        group.set_visible(True)

        for accel, title in [
            ("0 1 2 3 4 5 6 7 8 9", "Numbers"),
            ("plus minus asterisk slash", "Operators"),
            ("Return", "Calculate"),
            ("Escape", "Clear"),
            ("BackSpace", "Delete last"),
            ("<ctrl>h", "Toggle history"),
            ("percent", "Percent"),
            ("parenleft parenright", "Parentheses"),
        ]:
            s = Gtk.ShortcutsShortcut(accelerator=accel, title=title)
            s.set_visible(True)
            group.append(s)

        section.append(group)
        win.add_section(section)
        win.present()


def main():
    return App().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
