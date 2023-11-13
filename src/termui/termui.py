from math import log
import threading
import curses
import time
from turtle import color


# Why threaded ?
# Need to keep waiting for input yeah
class TermUi(threading.Thread):
    def __init__(self, callback):
        self.callback = callback
        self.terminate_flag = threading.Event()
        self.testing = True

        self.text_buffer = []
        self.prev_text_buffer = []

        self.user_input_buffer = []

        self.dummy_log_data = [
            "[ sys ][12:12]: testing",
            "[uname][12:13]: " + "jello" * 28 + "123" + "jello" * 28 + "123",
            "[uname][12:12]: yeah",
            "[uname][12:12]: " + "Henlo" * 28 + "123",
            "[hehee][12:12]: jello",
            "[uname][12:13]: " + "yeyoo" * 28 + "123",
        ]
        super(TermUi, self).__init__()

    # * Initialize
    def init_color(self):
        """
        Staring color and creating color pair

        :param self:    Attributes instance
        """
        curses.start_color()

        # * CAUTION , color_1
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_WHITE)

        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)

        # TITLE COLOR
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_WHITE)

        # SYS COLOR
        curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    def draw_window_border(self, win, title: str = "", attr=None, location=2):
        """
        Draw border to windows object

        by default:
        --Title------

        :param self:        Attributes instance
        :param win:         curses.window where border will be drawn
        :param title:       windows title to be writen
        :param attr:        title attributes
        :param location:    X coordinate within top border where title will be drawn
        """
        # draw border
        win.border()
        win.refresh()

        _, max_x = win.getmaxyx()

        if title != "":
            if len(title) < int(max_x / 2):
                # add padding first
                title = " " + title + " "
                if attr is None:
                    win.addstr(0, location, title)
                else:
                    win.addstr(0, location, title, attr)

            else:
                # chop the title
                title = " " + title[: int(len(title) / 2)] + " "
                if attr is None:
                    win.addstr(0, location, title)
                else:
                    win.addstr(0, location, title, attr)

        win.refresh()

    # * UPDATE
    def update_log(self, log_window, testing=False):
        max_y, max_x = log_window.getmaxyx()
        max_y = max_y - 1
        # print("Log Window max: {}, {}".format(max_x, max_y))

        curr_line = max_y
        # 16 if HH:MM
        # 19 if HH:MM:SS
        white_space = 16
        # * IF testing is True, use dummy data
        if testing and self.text_buffer == []:
            self.text_buffer = self.dummy_log_data.copy()

        # * First check whether
        # *  text_buffer equal to previous text buffer
        if self.text_buffer != self.prev_text_buffer:
            log_window.clear()
            log_window.refresh()
            # screen painting logic
            reversed_text_buffer = self.text_buffer.copy()
            reversed_text_buffer.reverse()
            # check if line fit?
            for text in reversed_text_buffer:
                # * We chop if more than 2 lines
                text = text[: max_x + (max_x - white_space)]

                if curr_line == max_y and len(text) > max_x:
                    log_window.addstr(curr_line, white_space, text[max_x:])
                    curr_line = curr_line - 1
                    log_window.addstr(curr_line, 0, text[:max_x])
                elif curr_line > 0:
                    if len(text) > max_x:
                        log_window.addstr(curr_line, white_space, text[max_x:])
                        curr_line = curr_line - 1
                        log_window.addstr(curr_line, 0, text[:max_x])
                        curr_line = curr_line - 1
                    else:
                        log_window.addstr(curr_line, 0, text)
                        curr_line = curr_line - 1
                elif curr_line == 0:
                    if len(text) > max_x:
                        log_window.addstr(curr_line, white_space, text[max_x:])
                        curr_line = curr_line - 1
                    else:
                        log_window.addstr(curr_line, 0, text)
                        curr_line = curr_line - 1

            log_window.refresh()
            self.prev_text_buffer = self.text_buffer[:]

    def update_fps_counter(self, win, fps: float):
        """
        Paint FPS amount in around top left

        :param self:    Attributes instance
        :param win:     curses.window instance, should be log_window_border
        :param fps:     Amount of loop per second
        """

        _, max_x = win.getmaxyx()
        erasure = "           "
        win.addstr(1, max_x - 12, erasure)
        fps_formating = "{:.6f}".format(fps)[:6]
        win.addstr(1, max_x - 14, "FPS: {}".format(fps_formating))
        win.refresh()

    def update_user_input_window(self, win, data=""):
        """
        Repaint user input window with data
        Reset it firse

        :param self:    Attributes instance
        :param win:     curses.window instance, should be user_input_window
        :param fps:     str to paint
        """

        win.clear()
        win.addstr(data)
        win.refresh()

    # * Threading Function
    def stop(self):
        """
        Stopping this Terminal UI, the view

        :param self:    Attributes instance
        """
        self.terminate_flag.set()

    def main(self, stdscr):
        """
        Main loop for Terminal UI, the view
        All win and stdscr etc, is here

        :param self:    Attributes instance
        """
        main_window_tite = "Term: Messaging App"
        self.init_color()

        max_y, max_x = stdscr.getmaxyx()
        stdscr.refresh()

        # * create 2 container windows
        # * chat log + input
        log_window_border = stdscr.subwin(max_y - 3, max_x, 0, 0)
        user_input_window_border = stdscr.subwin(3, max_x, max_y - 3, 0)

        self.draw_window_border(
            win=log_window_border,
            title=main_window_tite,
            attr=curses.color_pair(6) | curses.A_BOLD,
        )

        self.draw_window_border(
            win=user_input_window_border,
            title="Input : {} char max".format(max_x - 5),
            attr=curses.color_pair(0),
        )

        # * draw info
        info = "Connect: !conn  ||  Exit: !exit"
        log_window_border.addstr(1, 3, info)
        log_window_border.addstr(
            0, max_x - 25, " DON'T Resize Terminal ", curses.color_pair(1)
        )
        log_window_border.refresh()

        # * Log window info
        log_max_y, log_max_x = log_window_border.getmaxyx()
        log_max_y = log_max_y - 3
        log_max_x = log_max_x - 6
        log_window = curses.newwin(log_max_y, log_max_x, 2, 3)

        # * user_input window
        _, user_max_x = user_input_window_border.getmaxyx()
        user_input_window = curses.newwin(1, user_max_x - 4, max_y - 2, 3)
        user_input_window.timeout(10)

        # * Initial fps
        self.update_fps_counter(log_window_border, 0)
        # * HERE MAIN
        while not self.terminate_flag.is_set():
            start_time = time.time()
            time.sleep(0.01)
            # get input etc && handle
            # after input is acquired, pass it using callback
            buff = self.get_char(user_input_window)
            self.process_input_char(buff)
            self.update_user_input_window(
                win=user_input_window, data="".join(self.user_input_buffer)
            )
            # update log
            self.update_log(log_window=log_window, testing=self.testing)
            # * update_fps
            self.update_fps_counter(log_window_border, 1.0 / (time.time() - start_time))
            # * fps limiter
            # time.sleep(max(1.0 / 25 - (time.time() - start_time), 0))

    def run(self):
        """
        Function to start Terminal UI, the view

        :param self:    Attributes instance
        """
        curses.wrapper(self.main)
        # here is cleaning up

    # * Input get & processing
    def get_char(self, input_win) -> int:
        """
        Get char from user input with .1s delay by default

        :param self:        Attributes instance
        :param input_win:   curses.win Instances for input

        :return:            Unicode value of char
        """

        return input_win.getch()

    def process_input_char(self, char: int):
        """
        Process char in unicode we get from user input

        :param self:        Attributes instance
        :param char:        Integer unicode representation of character
        """
        # print("cuur_cahr: ", char)
        if 32 <= char <= 126:
            # From space -> tilde
            self.user_input_buffer.append(chr(char))

        elif char == 10:
            # Enter
            user_input_data = "".join(self.user_input_buffer).strip()
            self.user_input(user_input_data)
            self.user_input_buffer = []
            #! TEMPORARY
            self.text_buffer.append(user_input_data)

        elif char == 8 or char == 127 or char == curses.KEY_BACKSPACE:
            # Backspace
            self.user_input_buffer = self.user_input_buffer[:-1]

    # ? CALLBACK
    def user_input(self, u_input: str):
        """
        Callback function when user finish inputing data

        :param self:    Attributes instance
        :param u_input: User input in str
        """
        func_name = "user_input"
        self.callback("user_input", u_input)


if __name__ == "__main__":

    def henlo(t, u):
        print(t, ": ", u)

    x = TermUi(callback=henlo)
    x.start()

    time.sleep(6)

    x.stop()
