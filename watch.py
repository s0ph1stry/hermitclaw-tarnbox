"""Terminal monitor for HermitClaw — room at top, scrolling log below."""

import curses
import os
import sys
import time
import threading
import warnings

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import requests

BASE = "http://localhost:8000"
POLL_INTERVAL = 2

# Room layout matching brain.py
LOCATIONS = {
    (10, 1): "desk",
    (1, 2): "books",
    (4, 0): "wndw",
    (0, 8): "plnt",
    (3, 10): "bed",
    (5, 5): "rug",
}

COLLISION = set()
_rows = [
    "XXXX..XXXXXX",
    "..XX...XX...",
    ".......XXXX.",
    "..XX...XX...",
    "..XX...XX...",
    "........XX..",
    "............",
    "..XXXXXX..XX",
    "..XX...X..X.",
    "....XXX...X.",
    "XX...X.....X",
    "X....X......",
]
for _y, _row in enumerate(_rows):
    for _x, _ch in enumerate(_row):
        if _ch == "X":
            COLLISION.add((_x, _y))

# Room panel height: 1 name + 1 legend + 1 top border + 12 grid + 1 bottom border + 1 divider = 17
ROOM_HEIGHT = 17


class TarnWatch:
    def __init__(self):
        self.seen_events = 0
        self.position = (5, 5)
        self.state = "idle"
        self.thought_count = 0
        self.memory_count = 0
        self.name = "Tarn"
        self.log_lines = []
        self.input_buffer = ""
        self.cursor_pos = 0  # cursor position within input_buffer
        self.lock = threading.Lock()
        self.running = True
        # Scroll state: 0 means pinned to bottom, >0 means scrolled up by N lines
        self.scroll_offset = 0
        self.prev_log_len = 0  # track when new content arrives

    def add_log(self, text, style="normal"):
        with self.lock:
            self.log_lines.append((text, style))

    def poll(self):
        try:
            status = requests.get(f"{BASE}/api/status", timeout=5).json()
            self.position = (status["position"]["x"], status["position"]["y"])
            self.state = status["state"]
            self.thought_count = status["thought_count"]
            self.memory_count = status["memory_count"]
            self.name = status["name"]
        except Exception:
            pass

        try:
            resp = requests.get(f"{BASE}/api/events?limit=500", timeout=5)
            events = resp.json()
        except Exception:
            return

        new_events = events[self.seen_events:]
        self.seen_events = len(events)

        for e in new_events:
            t = e["type"]
            if t == "thought":
                text = e["text"].strip()
                self.add_log("")
                self.add_log(f"  {text}", "thought")
                self.add_log("")
            elif t == "tool_call":
                args = e.get("args", {})
                tool = e["tool"]
                if tool == "respond":
                    msg = args.get("message", "")
                    self.add_log("")
                    self.add_log(f"  {self.name}: {msg}", "speech")
                    self.add_log("")
                elif tool == "shell":
                    cmd = args.get("command", "")
                    self.add_log(f"  $ {cmd}", "shell")
                elif tool == "move":
                    loc = args.get("location", "")
                    self.add_log(f"  [moves to {loc}]", "dim")
            elif t == "tool_result":
                tool = e.get("tool", "")
                output = str(e.get("output", ""))
                if tool == "respond":
                    if "No reply" in output:
                        self.add_log("  (waiting for reply...)", "dim")
                    elif "They say" in output:
                        self.add_log(f"  {output}", "input")
                elif tool == "shell" and output.strip() and output != "(no output)":
                    lines = output.strip().split("\n")
                    for line in lines[:8]:
                        self.add_log(f"    {line}", "dim")
                    if len(lines) > 8:
                        self.add_log(f"    ...({len(lines) - 8} more lines)", "dim")
            elif t == "reflection":
                self.add_log("")
                self.add_log(f"  reflection: {e.get('text', '')}", "reflection")
                self.add_log("")
            elif t == "planning":
                self.add_log("")
                self.add_log("  planning cycle complete", "dim")
                self.add_log("")

    def send_message(self, text):
        try:
            resp = requests.post(f"{BASE}/api/message",
                               json={"text": text}, timeout=5)
            if resp.json().get("ok"):
                self.add_log("")
                self.add_log(f"  You: {text}", "input")
                self.add_log("")
        except Exception:
            self.add_log("  (failed to send)", "dim")

    def draw_room(self, stdscr, max_w):
        """Draw room pinned at the top of the screen."""
        px, py = self.position
        row = 0

        # Name and status on one line
        header = f" {self.name}  "
        state_str = f"{self.state} | t:{self.thought_count} m:{self.memory_count}"
        try:
            stdscr.addnstr(row, 0, header, max_w - 1, curses.A_BOLD | curses.color_pair(1))
            stdscr.addnstr(row, len(header), state_str, max_w - len(header) - 1, curses.A_DIM)
        except curses.error:
            pass
        row += 1

        # Legend inline
        legend = "  D=desk  B=books  W=window  P=plant  Z=bed  R=rug"
        try:
            stdscr.addnstr(row, 0, legend, max_w - 1, curses.A_DIM)
        except curses.error:
            pass
        row += 1

        # Room grid — 2 chars per cell so it looks square
        cell_w = 2
        grid_w = 12 * cell_w
        border_top = "  +" + "-" * grid_w + "+"
        try:
            stdscr.addnstr(row, 0, border_top, max_w - 1, curses.A_DIM)
        except curses.error:
            pass
        row += 1

        for y in range(12):
            line = "  |"
            for x in range(12):
                if x == px and y == py:
                    line += "@" + " " * (cell_w - 1)
                elif (x, y) in LOCATIONS:
                    label = LOCATIONS[(x, y)][0].upper()
                    line += label + " " * (cell_w - 1)
                elif (x, y) in COLLISION:
                    line += "#" + " " * (cell_w - 1)
                else:
                    line += "." + " " * (cell_w - 1)
            line += "|"
            try:
                stdscr.addnstr(row, 0, line, max_w - 1, curses.A_DIM)
                # Highlight Tarn and locations
                for x2 in range(12):
                    c = 3 + x2 * cell_w  # 2 indent + 1 border + cell offset
                    if c >= max_w:
                        break
                    if x2 == px and y == py:
                        stdscr.chgat(row, c, 1, curses.A_BOLD | curses.color_pair(1))
                    elif (x2, y) in LOCATIONS:
                        stdscr.chgat(row, c, 1, curses.color_pair(3))
            except curses.error:
                pass
            row += 1

        border_bot = "  +" + "-" * grid_w + "+"
        try:
            stdscr.addnstr(row, 0, border_bot, max_w - 1, curses.A_DIM)
        except curses.error:
            pass
        row += 1

        # Horizontal divider
        try:
            stdscr.addnstr(row, 0, "-" * max_w, max_w - 1, curses.A_DIM)
        except curses.error:
            pass

        return row + 1  # first row available for log

    def _wrap_log_lines(self, content_width):
        """Word-wrap all log lines to the given width. Returns list of (text, style)."""
        wrapped = []
        for text, style in self.log_lines:
            if len(text) <= content_width:
                wrapped.append((text, style))
            else:
                remaining = text
                while len(remaining) > content_width:
                    break_at = remaining.rfind(" ", 0, content_width)
                    if break_at <= 0:
                        break_at = content_width
                    wrapped.append((remaining[:break_at], style))
                    remaining = "    " + remaining[break_at:].lstrip()
                if remaining:
                    wrapped.append((remaining, style))
        return wrapped

    def draw_log(self, stdscr, start_row, max_h, max_w):
        """Draw scrolling log below the room, input at bottom."""
        # Reserve bottom 2 rows: one for scroll indicator, one for input
        available = max_h - start_row - 2
        if available < 1:
            return

        content_width = max_w - 1
        if content_width < 10:
            return

        with self.lock:
            wrapped = self._wrap_log_lines(content_width)
            total = len(wrapped)
            cur_log_len = len(self.log_lines)

            # Auto-scroll: if new content arrived and we were at the bottom, stay there
            if cur_log_len > self.prev_log_len:
                if self.scroll_offset == 0:
                    pass  # already pinned to bottom
                # If user is scrolled up, don't move them
            self.prev_log_len = cur_log_len

            # Clamp scroll offset
            max_scroll = max(0, total - available)
            if self.scroll_offset > max_scroll:
                self.scroll_offset = max_scroll

            # Determine the visible window
            if total <= available:
                # Everything fits, no scrolling needed
                visible = wrapped
            else:
                # end is the index one past the last visible line
                end = total - self.scroll_offset
                start = max(0, end - available)
                visible = wrapped[start:end]

        for i, (text, style) in enumerate(visible):
            row = start_row + i
            if row >= max_h - 2:
                break
            attr = curses.A_NORMAL
            if style == "thought":
                attr = curses.color_pair(2)
            elif style == "speech":
                attr = curses.A_BOLD | curses.color_pair(1)
            elif style == "shell":
                attr = curses.color_pair(3)
            elif style == "dim":
                attr = curses.A_DIM
            elif style == "reflection":
                attr = curses.color_pair(4)
            elif style == "input":
                attr = curses.color_pair(5)
            try:
                stdscr.addnstr(row, 0, text, max_w - 1, attr)
            except curses.error:
                pass

        # Scroll indicator on the line just above input
        indicator_row = max_h - 2
        if self.scroll_offset > 0:
            indicator = f" [scrolled up {self.scroll_offset} lines — PgDn/End to return] "
            try:
                stdscr.addnstr(indicator_row, 0, indicator, max_w - 1, curses.A_DIM | curses.A_REVERSE)
            except curses.error:
                pass

        # Input line at very bottom
        input_row = max_h - 1
        prompt = f"> {self.input_buffer}"
        try:
            stdscr.addnstr(input_row, 0, prompt, max_w - 1, curses.A_BOLD)
        except curses.error:
            pass

        # Position the cursor at the typing location so it's visible
        cursor_x = 2 + self.cursor_pos  # ">" + space + cursor_pos chars into buffer
        if cursor_x >= max_w:
            cursor_x = max_w - 1
        try:
            stdscr.move(input_row, cursor_x)
        except curses.error:
            pass

    def run_curses(self, stdscr):
        # Show the cursor so the user can see where they're typing
        try:
            curses.curs_set(1)
        except curses.error:
            pass  # some terminals don't support cursor visibility

        # Use timeout mode: getch blocks for up to 100ms then returns -1.
        # This replaces nodelay(True) which caused a busy spin loop.
        stdscr.timeout(100)

        # Enable keypad mode so special keys (arrows, Page Up/Down, etc.) are decoded
        stdscr.keypad(True)

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # speech / tarn
        curses.init_pair(2, curses.COLOR_CYAN, -1)     # thought
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # shell / locations
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # reflection
        curses.init_pair(5, curses.COLOR_BLUE, -1)     # user input

        self.add_log("  Connecting...", "dim")
        connected = False
        for attempt in range(10):
            try:
                status = requests.get(f"{BASE}/api/status", timeout=5).json()
                self.name = status["name"]
                self.position = (status["position"]["x"], status["position"]["y"])
                self.state = status["state"]
                self.thought_count = status["thought_count"]
                self.memory_count = status["memory_count"]
                connected = True
                break
            except Exception:
                time.sleep(2)

        if not connected:
            self.add_log("  Can't reach hermitclaw. Is it running?", "dim")
            time.sleep(3)
            return

        try:
            events = requests.get(f"{BASE}/api/events?limit=500", timeout=5).json()
            self.seen_events = len(events)
        except Exception:
            pass

        self.add_log(f"  Watching {self.name} — type a message and press Enter", "dim")
        self.add_log(f"  PgUp/PgDn to scroll, End to jump to bottom, ESC to quit", "dim")
        self.add_log("")

        def poll_loop():
            while self.running:
                self.poll()
                time.sleep(POLL_INTERVAL)

        poll_thread = threading.Thread(target=poll_loop, daemon=True)
        poll_thread.start()

        while self.running:
            try:
                ch = stdscr.getch()
            except curses.error:
                ch = -1

            if ch == -1:
                # No input — just redraw and continue
                pass
            elif ch == 27:  # ESC
                # Peek for a follow-up character to distinguish ESC from Alt sequences.
                # With timeout mode, if ESC is pressed alone, the next getch returns -1.
                stdscr.nodelay(True)
                ch2 = stdscr.getch()
                stdscr.nodelay(False)
                stdscr.timeout(100)
                if ch2 == -1:
                    # Bare ESC — quit
                    self.running = False
                    break
                # Otherwise it's an alt/escape sequence; ignore it
            elif ch in (curses.KEY_ENTER, 10, 13):
                if self.input_buffer.strip():
                    msg = self.input_buffer.strip()
                    self.input_buffer = ""
                    self.cursor_pos = 0
                    # Sending a message means the user wants to see the response
                    self.scroll_offset = 0
                    threading.Thread(
                        target=self.send_message, args=(msg,), daemon=True
                    ).start()
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                if self.cursor_pos > 0:
                    self.input_buffer = (
                        self.input_buffer[:self.cursor_pos - 1]
                        + self.input_buffer[self.cursor_pos:]
                    )
                    self.cursor_pos -= 1
            elif ch == curses.KEY_DC:  # Delete key
                if self.cursor_pos < len(self.input_buffer):
                    self.input_buffer = (
                        self.input_buffer[:self.cursor_pos]
                        + self.input_buffer[self.cursor_pos + 1:]
                    )
            elif ch == curses.KEY_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
            elif ch == curses.KEY_RIGHT:
                if self.cursor_pos < len(self.input_buffer):
                    self.cursor_pos += 1
            elif ch == curses.KEY_HOME:
                self.cursor_pos = 0
            elif ch == curses.KEY_PPAGE:  # Page Up
                max_h, max_w = stdscr.getmaxyx()
                page_size = max(1, max_h - ROOM_HEIGHT - 4)
                self.scroll_offset += page_size
            elif ch == curses.KEY_NPAGE:  # Page Down
                max_h, max_w = stdscr.getmaxyx()
                page_size = max(1, max_h - ROOM_HEIGHT - 4)
                self.scroll_offset = max(0, self.scroll_offset - page_size)
            elif ch == curses.KEY_END:
                self.scroll_offset = 0
            elif ch == curses.KEY_UP:
                self.scroll_offset += 3
            elif ch == curses.KEY_DOWN:
                self.scroll_offset = max(0, self.scroll_offset - 3)
            elif 32 <= ch <= 126:
                self.input_buffer = (
                    self.input_buffer[:self.cursor_pos]
                    + chr(ch)
                    + self.input_buffer[self.cursor_pos:]
                )
                self.cursor_pos += 1

            # Redraw every iteration (getch already rate-limits via timeout)
            max_h, max_w = stdscr.getmaxyx()
            if max_h < 20 or max_w < 30:
                continue

            stdscr.erase()

            log_start = self.draw_room(stdscr, max_w)
            self.draw_log(stdscr, log_start, max_h, max_w)

            stdscr.refresh()

        self.running = False


def main():
    watch = TarnWatch()
    try:
        curses.wrapper(watch.run_curses)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
