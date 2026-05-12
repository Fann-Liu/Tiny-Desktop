import subprocess
import threading
import time
import tkinter as tk


READ_WINDOWS_SCRIPT = r'''
tell application "System Events"
    set outputText to ""
    repeat with proc in application processes
        try
            if background only of proc is false then
                set appName to name of proc as text
                set appVisible to visible of proc as text
                set windowCount to count of windows of proc

                if windowCount is 0 then
                    set outputText to outputText & appName & "|||" & appName & "|||" & 0 & "|||" & appVisible & "|||false|||app" & linefeed
                else
                    repeat with i from 1 to windowCount
                        try
                            set w to window i of proc
                            set windowName to ""
                            set minimizedText to "false"

                            try
                                set windowName to name of w as text
                            end try

                            if windowName is "" then
                                try
                                    set windowName to description of w as text
                                end try
                            end if

                            if windowName is "" then
                                set windowName to "Untitled Window"
                            end if

                            try
                                set minimizedText to value of attribute "AXMinimized" of w as text
                            end try

                            set outputText to outputText & appName & "|||" & windowName & "|||" & i & "|||" & appVisible & "|||" & minimizedText & "|||window" & linefeed
                        end try
                    end repeat
                end if
            end if
        end try
    end repeat
end tell

try
    tell application "System Events" to set safariRunning to exists (application process "Safari")
    if safariRunning then
        tell application "Safari"
            repeat with wi from 1 to (count of windows)
                try
                    set tabCount to count of tabs of window wi
                    repeat with ti from 1 to tabCount
                        try
                            set tabTitle to name of item ti of tabs of window wi as text
                            if tabTitle is "" then
                                set tabTitle to "Untitled Tab"
                            end if
                            set outputText to outputText & "Safari" & "|||" & tabTitle & "|||" & wi & "|||true|||false|||tab|||" & ti & linefeed
                        end try
                    end repeat
                end try
            end repeat
        end tell
    end if
end try

return outputText
'''


SWITCH_WINDOW_SCRIPT = r'''
on run argv
    set targetApp to item 1 of argv
    set targetWindowName to item 2 of argv
    set targetWindowIndex to item 3 of argv as integer
    set targetItemType to "window"
    set targetTabIndex to 0

    if (count of argv) >= 4 then
        set targetItemType to item 4 of argv
    end if

    if (count of argv) >= 5 then
        set targetTabIndex to item 5 of argv as integer
    end if

    tell application targetApp to activate

    if targetApp is "Safari" and targetItemType is "tab" and targetTabIndex > 0 then
        try
            tell application "Safari"
                set current tab of window targetWindowIndex to item targetTabIndex of tabs of window targetWindowIndex
                set index of window targetWindowIndex to 1
                activate
            end tell

            delay 0.1

            tell application "System Events"
                tell process "Safari"
                    try
                        set value of attribute "AXMinimized" of window 1 to false
                    end try
                    try
                        perform action "AXRaise" of window 1
                    end try
                end tell
            end tell

            return "OK"
        end try
    end if

    if targetWindowIndex is 0 then
        try
            tell application targetApp to reopen
        end try

        if targetApp is "微信" or targetApp is "WeChat" or targetApp is "Weixin" then
            try
                open location "wechat://"
            end try

            try
                open location "weixin://"
            end try
        end if

        try
            do shell script "open -a " & quoted form of targetApp
        end try

        delay 0.2

        tell application "System Events"
            try
                tell process targetApp
                    set frontmost to true

                    try
                        if (count of windows) > 0 then
                            try
                                set value of attribute "AXMinimized" of window 1 to false
                            end try
                            perform action "AXRaise" of window 1
                            return "OK"
                        end if
                    end try

                    if targetApp is "微信" or targetApp is "WeChat" or targetApp is "Weixin" then
                        try
                            keystroke "0" using command down
                            delay 0.2
                        end try

                        try
                            if (count of windows) > 0 then
                                try
                                    set value of attribute "AXMinimized" of window 1 to false
                                end try
                                perform action "AXRaise" of window 1
                                return "OK"
                            end if
                        end try

                        try
                            click menu item "微信" of menu "窗口" of menu bar item "窗口" of menu bar 1
                            return "OK"
                        end try

                        try
                            click menu item "WeChat" of menu "Window" of menu bar item "Window" of menu bar 1
                            return "OK"
                        end try

                        try
                            tell application "System Events"
                                tell process "Dock"
                                    try
                                        click UI element "微信" of list 1
                                        delay 0.2
                                    end try
                                    try
                                        click UI element "WeChat" of list 1
                                        delay 0.2
                                    end try
                                    try
                                        click UI element "Weixin" of list 1
                                        delay 0.2
                                    end try
                                end tell
                            end tell
                        end try

                        try
                            if (count of windows) > 0 then
                                try
                                    set value of attribute "AXMinimized" of window 1 to false
                                end try
                                perform action "AXRaise" of window 1
                                return "OK"
                            end if
                        end try

                        return "OK"
                    end if
                end tell
            end try
        end tell

        return "OK"
    end if

    tell application "System Events"
        tell process targetApp
            try
                try
                    set value of attribute "AXMinimized" of window targetWindowIndex to false
                end try
                perform action "AXRaise" of window targetWindowIndex
                return "OK"
            on error
                repeat with w in windows
                    if name of w is targetWindowName then
                        try
                            set value of attribute "AXMinimized" of w to false
                        end try
                        perform action "AXRaise" of w
                        return "OK"
                    end if
                end repeat
            end try
        end tell
    end tell

    return "Window not found"
end run
'''


class WindowNavigator:
    AUTO_REFRESH_MS = 5000
    MIN_WIDTH = 320
    MIN_HEIGHT = 320
    GROUP_ROW_HEIGHT = 58
    CHILD_ROW_HEIGHT = 54

    def __init__(self, root):
        self.root = root
        self.windows = []
        self.rows = []
        self.expanded_apps = set()
        self.selected_key = None
        self.refresh_in_progress = False
        self.closed = False

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0

        self.colors = {
            "window": "#f2f2f7",
            "card": "#fbfbfd",
            "card_hover": "#f4f4f8",
            "line": "#d8d8df",
            "text": "#1d1d1f",
            "muted": "#6e6e73",
            "accent": "#007aff",
            "chip": "#e9e9ef",
            "error": "#c9352b",
        }

        self.root.title("小小桌面")
        self.root.geometry("360x460+56+96")
        self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.97)
        self.root.overrideredirect(True)
        self.root.configure(bg=self.colors["window"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.build_ui()
        self.bind_events()

        self.refresh()
        self.schedule_auto_refresh()

    def build_ui(self):
        self.header = tk.Frame(self.root, bg=self.colors["window"], height=64)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        self.title_label = tk.Label(
            self.header,
            text="小小桌面",
            bg=self.colors["window"],
            fg=self.colors["text"],
            font=("SF Pro Display", 22, "bold"),
            anchor=tk.W,
        )
        self.title_label.pack(side=tk.LEFT, padx=(18, 8), pady=(16, 12))

        self.count_label = tk.Label(
            self.header,
            text="0",
            bg=self.colors["window"],
            fg=self.colors["muted"],
            font=("SF Pro Text", 12),
            anchor=tk.W,
        )
        self.count_label.pack(side=tk.LEFT, pady=(22, 12))

        self.close_button = self.make_icon_button("×", self.close)
        self.close_button.pack(side=tk.RIGHT, padx=(4, 14), pady=(18, 14))

        self.refresh_button = self.make_icon_button("↻", self.refresh)
        self.refresh_button.pack(side=tk.RIGHT, padx=(4, 0), pady=(18, 14))

        self.body = tk.Frame(self.root, bg=self.colors["window"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.canvas = tk.Canvas(
            self.body,
            bg=self.colors["card"],
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollincrement=12,
        )
        self.scrollbar = tk.Scrollbar(
            self.body,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.footer = tk.Frame(self.root, bg=self.colors["window"], height=34)
        self.footer.pack(fill=tk.X)
        self.footer.pack_propagate(False)

        self.status_label = tk.Label(
            self.footer,
            text="Loading…",
            bg=self.colors["window"],
            fg=self.colors["muted"],
            anchor=tk.W,
            font=("SF Pro Text", 11),
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 6), pady=(0, 10))

        self.resize_grip = tk.Label(
            self.footer,
            text="◢",
            bg=self.colors["window"],
            fg="#b8b8bf",
            font=("SF Pro Text", 12),
            cursor="arrow",
        )
        self.resize_grip.pack(side=tk.RIGHT, padx=(4, 12), pady=(0, 8))

    def make_icon_button(self, text, command):
        return tk.Button(
            self.header,
            text=text,
            command=command,
            bg=self.colors["chip"],
            fg=self.colors["text"],
            activebackground="#dedee5",
            activeforeground=self.colors["text"],
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            font=("SF Pro Text", 15),
            width=3,
            cursor="arrow",
        )

    def bind_events(self):
        self.root.bind("<Escape>", lambda event: self.close())
        self.root.bind("<Return>", self.open_selected)
        self.root.bind("<Configure>", self.redraw_soon)

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))

        for widget in (self.header, self.title_label, self.count_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag_window)

        self.resize_grip.bind("<ButtonPress-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.resize_window)

    def start_drag(self, event):
        self.drag_start_x = event.x_root - self.root.winfo_x()
        self.drag_start_y = event.y_root - self.root.winfo_y()

    def drag_window(self, event):
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_width = self.root.winfo_width()
        self.resize_start_height = self.root.winfo_height()

    def resize_window(self, event):
        width = max(self.MIN_WIDTH, self.resize_start_width + event.x_root - self.resize_start_x)
        height = max(self.MIN_HEIGHT, self.resize_start_height + event.y_root - self.resize_start_y)
        self.root.geometry(f"{width}x{height}")

    def schedule_auto_refresh(self):
        if not self.closed:
            self.root.after(self.AUTO_REFRESH_MS, self.auto_refresh)

    def auto_refresh(self):
        self.refresh()
        self.schedule_auto_refresh()

    def refresh(self):
        if self.refresh_in_progress:
            return

        self.refresh_in_progress = True
        self.set_status("Updating…")
        self.refresh_button.configure(state=tk.DISABLED)

        worker = threading.Thread(target=self.read_windows_worker, daemon=True)
        worker.start()

    def read_windows_worker(self):
        try:
            windows = read_windows()
            error = None
        except RuntimeError as exc:
            windows = []
            error = exc

        self.root.after(0, lambda: self.finish_refresh(windows, error))

    def finish_refresh(self, windows, error):
        self.refresh_in_progress = False
        self.refresh_button.configure(state=tk.NORMAL)

        if error:
            print(error)
            self.set_status("Enable Accessibility permission")
            self.status_label.configure(fg=self.colors["error"])
            return

        self.status_label.configure(fg=self.colors["muted"])
        self.windows = windows

        if self.selected_key not in {window_key(window) for window in self.windows}:
            self.selected_key = None

        self.draw_rows()
        self.count_label.configure(text=f"{len(group_windows(self.windows))} apps")
        self.set_status(f"Updated {time.strftime('%H:%M')}")

    def redraw_soon(self, event=None):
        if event and event.widget is not self.root:
            return
        self.root.after_idle(self.draw_rows)

    def draw_rows(self):
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("all")
        self.rows = build_visible_rows(self.windows, self.expanded_apps)

        width = max(self.canvas.winfo_width(), self.MIN_WIDTH - 28)
        if width <= 1:
            width = self.MIN_WIDTH - 28

        if not self.rows:
            self.canvas.create_text(
                width / 2,
                120,
                text="No windows",
                fill=self.colors["muted"],
                font=("SF Pro Text", 14),
            )
            self.canvas.configure(scrollregion=(0, 0, width, 240))
            return

        y = 0
        for index, row in enumerate(self.rows):
            row_tag = f"row-{index}"

            if row["kind"] == "group":
                height = self.GROUP_ROW_HEIGHT
                app_name = row["app_name"]
                children = row["children"]
                is_expanded = app_name in self.expanded_apps
                is_open_app = len(children) == 1 and children[0].get("item_type") == "app"
                row_bg = self.colors["card"]

                self.canvas.create_rectangle(
                    0,
                    y,
                    width,
                    y + height,
                    fill=row_bg,
                    outline="",
                    tags=(row_tag,),
                )

                if index:
                    self.canvas.create_line(
                        16,
                        y,
                        width - 14,
                        y,
                        fill=self.colors["line"],
                        tags=(row_tag,),
                    )

                arrow = "›" if not is_expanded else "⌄"
                if is_open_app:
                    arrow = " "
                self.canvas.create_text(
                    20,
                    y + 29,
                    text=arrow,
                    fill=self.colors["muted"],
                    font=("SF Pro Text", 18, "bold"),
                    tags=(row_tag,),
                )

                badge_color = app_color(app_name)
                self.canvas.create_oval(
                    36,
                    y + 15,
                    64,
                    y + 43,
                    fill=badge_color,
                    outline="",
                    tags=(row_tag,),
                )
                self.canvas.create_text(
                    50,
                    y + 29,
                    text=app_initial(app_name),
                    fill="#ffffff",
                    font=("SF Pro Text", 12, "bold"),
                    tags=(row_tag,),
                )

                title = fit_text(app_name, max(18, int((width - 120) / 7)))
                subtitle = fit_text(group_subtitle(children), max(18, int((width - 120) / 7)))
                self.canvas.create_text(
                    76,
                    y + 21,
                    text=title,
                    fill=self.colors["text"],
                    font=("SF Pro Text", 13, "bold"),
                    anchor=tk.W,
                    tags=(row_tag,),
                )
                self.canvas.create_text(
                    76,
                    y + 40,
                    text=subtitle,
                    fill=self.colors["muted"],
                    font=("SF Pro Text", 11),
                    anchor=tk.W,
                    tags=(row_tag,),
                )

                if is_open_app:
                    self.canvas.tag_bind(row_tag, "<Button-1>", lambda event, i=index: self.activate_row(i))
                else:
                    self.canvas.tag_bind(row_tag, "<Button-1>", lambda event, app=app_name: self.toggle_group(app))

                self.canvas.tag_bind(row_tag, "<Enter>", lambda event: self.set_row_cursor())
                self.canvas.tag_bind(row_tag, "<Leave>", lambda event: self.canvas.configure(cursor=""))
                y += height
                continue

            window = row["window"]
            height = self.CHILD_ROW_HEIGHT
            key = window_key(window)
            is_selected = key == self.selected_key
            row_bg = "#eef5ff" if is_selected else self.colors["card"]

            self.canvas.create_rectangle(
                0,
                y,
                width,
                y + height,
                fill=row_bg,
                outline="",
                tags=(row_tag,),
            )

            self.canvas.create_line(
                76,
                y,
                width - 14,
                y,
                fill=self.colors["line"],
                tags=(row_tag,),
            )

            marker = "•"
            if window.get("item_type") == "tab":
                marker = "◦"
            self.canvas.create_text(
                50,
                y + 27,
                text=marker,
                fill=self.colors["accent"],
                font=("SF Pro Text", 18),
                tags=(row_tag,),
            )

            title = fit_text(window_title(window), max(18, int((width - 86) / 7)))
            subtitle = fit_text(window_subtitle(window), max(18, int((width - 86) / 7)))
            self.canvas.create_text(
                76,
                y + 18,
                text=title,
                fill=self.colors["text"],
                font=("SF Pro Text", 12, "bold"),
                anchor=tk.W,
                tags=(row_tag,),
            )
            self.canvas.create_text(
                76,
                y + 37,
                text=subtitle,
                fill=self.colors["muted"],
                font=("SF Pro Text", 11),
                anchor=tk.W,
                tags=(row_tag,),
            )

            self.canvas.tag_bind(row_tag, "<Button-1>", lambda event, i=index: self.activate_row(i))
            self.canvas.tag_bind(row_tag, "<Enter>", lambda event: self.set_row_cursor())
            self.canvas.tag_bind(row_tag, "<Leave>", lambda event: self.canvas.configure(cursor=""))
            y += height

        self.canvas.configure(scrollregion=(0, 0, width, y))

    def set_row_cursor(self):
        self.canvas.configure(cursor="hand2")

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def open_selected(self, event=None):
        if not self.rows:
            return

        if self.selected_key:
            for index, row in enumerate(self.rows):
                if row["kind"] == "item" and window_key(row["window"]) == self.selected_key:
                    self.activate_row(index)
                    return

        self.activate_row(0)

    def activate_row(self, index):
        if index < 0 or index >= len(self.rows):
            return

        row = self.rows[index]
        if row["kind"] == "group":
            children = row["children"]
            if len(children) == 1 and children[0].get("item_type") == "app":
                window = children[0]
            else:
                self.toggle_group(row["app_name"])
                return
        else:
            window = row["window"]

        self.selected_key = window_key(window)
        self.draw_rows()
        self.set_status(f"Opening {window['app_name']}…")

        worker = threading.Thread(target=self.switch_worker, args=(window,), daemon=True)
        worker.start()

    def toggle_group(self, app_name):
        if app_name in self.expanded_apps:
            self.expanded_apps.remove(app_name)
        else:
            self.expanded_apps.add(app_name)
        self.draw_rows()

    def switch_worker(self, window):
        try:
            switch_to_window(
                window["app_name"],
                window["window_name"],
                window["window_index"],
                window.get("item_type", "window"),
                window.get("tab_index", 0),
            )
            error = None
        except RuntimeError as exc:
            error = exc

        self.root.after(0, lambda: self.finish_switch(window, error))

    def finish_switch(self, window, error):
        if error:
            print(error)
            self.status_label.configure(fg=self.colors["error"])
            self.set_status("Failed to switch window")
            return

        self.status_label.configure(fg=self.colors["muted"])
        self.set_status(f"Opened {window['app_name']}")

    def set_status(self, text):
        self.status_label.configure(text=text)

    def close(self):
        self.closed = True
        self.root.destroy()


def run_osascript(script, args=None):
    command = ["osascript", "-e", script]
    if args:
        command.extend(str(arg) for arg in args)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("osascript timed out") from exc

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "osascript failed")

    return result.stdout


def read_windows():
    output = run_osascript(READ_WINDOWS_SCRIPT)
    windows = []

    for line in output.splitlines():
        parts = line.split("|||")
        if len(parts) < 3:
            continue

        app_name = parts[0]
        window_name = parts[1]
        window_index = parts[2]
        app_visible = parts[3] if len(parts) > 3 else "true"
        minimized = parts[4] if len(parts) > 4 else "false"
        item_type = parts[5] if len(parts) > 5 else "window"
        tab_index = parts[6] if len(parts) > 6 else "0"
        if not app_name or not window_name:
            continue

        try:
            parsed_index = int(window_index)
        except ValueError:
            continue

        try:
            parsed_tab_index = int(tab_index)
        except ValueError:
            parsed_tab_index = 0

        windows.append(
            {
                "app_name": app_name,
                "window_name": window_name,
                "window_index": parsed_index,
                "app_visible": app_visible == "true",
                "minimized": minimized == "true",
                "item_type": item_type,
                "tab_index": parsed_tab_index,
            }
        )

    safari_has_tabs = any(
        item["app_name"] == "Safari" and item.get("item_type") == "tab"
        for item in windows
    )
    if safari_has_tabs:
        windows = [
            item
            for item in windows
            if not (item["app_name"] == "Safari" and item.get("item_type") == "window")
        ]

    windows.sort(key=lambda item: (item["app_name"].lower(), item["window_name"].lower()))
    return windows


def switch_to_window(app_name, window_name, window_index, item_type="window", tab_index=0):
    output = run_osascript(
        SWITCH_WINDOW_SCRIPT,
        [app_name, window_name, window_index, item_type, tab_index],
    ).strip()

    if output != "OK":
        raise RuntimeError(output or "Window not found")


def window_key(window):
    return (
        window["app_name"],
        window["window_name"],
        window["window_index"],
        window.get("item_type", "window"),
        window.get("tab_index", 0),
    )


def group_windows(windows):
    groups = {}
    for window in windows:
        groups.setdefault(window["app_name"], []).append(window)
    return dict(sorted(groups.items(), key=lambda item: item[0].lower()))


def build_visible_rows(windows, expanded_apps):
    rows = []
    for app_name, children in group_windows(windows).items():
        rows.append(
            {
                "kind": "group",
                "app_name": app_name,
                "children": children,
            }
        )
        if app_name in expanded_apps:
            for child in children:
                rows.append(
                    {
                        "kind": "item",
                        "app_name": app_name,
                        "window": child,
                    }
                )
    return rows


def group_subtitle(children):
    if len(children) == 1 and children[0].get("item_type") == "app":
        return "Open App · running, no window"

    tab_count = sum(1 for child in children if child.get("item_type") == "tab")
    window_count = sum(1 for child in children if child.get("item_type") == "window")
    minimized_count = sum(1 for child in children if child.get("minimized"))
    hidden_count = sum(1 for child in children if child.get("app_visible") is False)

    parts = []
    if tab_count:
        parts.append(f"{tab_count} tabs")
    if window_count:
        parts.append(f"{window_count} windows")
    if minimized_count:
        parts.append(f"{minimized_count} minimized")
    if hidden_count:
        parts.append("hidden")
    return " · ".join(parts) if parts else f"{len(children)} items"


def window_subtitle(window):
    status = []
    if window.get("item_type") == "app":
        status.append("Open App")
        status.append("running, no window")
    if window.get("item_type") == "tab":
        status.append("Safari Tab")
    if window.get("minimized"):
        status.append("minimized")
    if window.get("app_visible") is False:
        status.append("hidden")

    if status:
        return f'{window["app_name"]} · {", ".join(status)}'
    return window["app_name"]


def window_title(window):
    if window.get("item_type") == "app":
        return window["app_name"]
    return window["window_name"]


def fit_text(text, limit):
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def app_initial(app_name):
    stripped = app_name.strip()
    if not stripped:
        return "?"
    return stripped[0].upper()


def app_color(app_name):
    palette = [
        "#007aff",
        "#34c759",
        "#ff9500",
        "#ff3b30",
        "#5856d6",
        "#00c7be",
        "#af52de",
        "#8e8e93",
    ]
    return palette[sum(ord(ch) for ch in app_name) % len(palette)]


def main():
    root = tk.Tk()
    WindowNavigator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
