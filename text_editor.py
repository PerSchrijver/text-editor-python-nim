#!/usr/bin/env python3.10
from dataclasses import dataclass, replace
import pickle
import string
from typing import NamedTuple, Tuple
import pygame

# Initialize performance necessary constants
DISPLAYABLE_CHARACTERS = set(string.printable) - set(" \t\r\n\x0b\x0c")

# Initialize screen
screen_width, screen_height = 1280, 720
LEFT_PADDING = 400
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
pygame.init()

# Enable key repeating
pygame.key.set_repeat(300, 1000 // 20)

# Editor classes
@dataclass(frozen=True)
class Line:
    font: pygame.font.Font
    size: int
    text: str
    space_before: int

    def splitted_for_newline(self, row: int, big_newline: bool) -> Tuple["Line", "Line"]:
        first = replace(self, text=self.text[:row])
        if big_newline:
            second = Line(*REGULAR_FONT_AND_SIZE, self.text[row:], 8)
        else:
            second = Line(*REGULAR_FONT_AND_SIZE, self.text[row:], 0)
        return first, second


@dataclass
class TypingAction:
    insert_line: int
    insert_row: int
    content: str

    def do(self):
        global cursor_row
        text = lines[self.insert_line].text
        lines[self.insert_line] = replace(
            lines[self.insert_line], text=text[: self.insert_row] + self.content + text[self.insert_row :]
        )
        cursor_row = self.insert_row + 1

    def undo(self):
        global cursor_row, cursor_line
        text = lines[self.insert_line].text
        undone_text = text[: self.insert_row] + text[len(self.content) + self.insert_row :]
        lines[self.insert_line] = replace(lines[self.insert_line], text=undone_text)
        cursor_row = self.insert_row
        cursor_line = self.insert_line


@dataclass
class NewlineAction:
    from_line: int
    from_row: int
    line_content: str
    big_new_line: bool

    def do(self):
        global cursor_line, cursor_row
        first, second = lines[self.from_line].splitted_for_newline(row=self.from_row, big_newline=self.big_new_line)
        lines[self.from_line] = first
        lines.insert(self.from_line + 1, second)
        cursor_line = self.from_line + 1
        cursor_row = 0

    def undo(self):
        global cursor_row, cursor_line
        lines[self.from_line] = replace(lines[self.from_line], text=self.line_content)
        lines.pop(self.from_line + 1)
        cursor_row = self.from_row
        cursor_line = self.from_line


@dataclass
class BackspaceCharacterAction:
    from_line: int
    from_row: int
    content: str

    def do(self):
        global cursor_row
        text = lines[self.from_line].text
        lines[self.from_line] = replace(
            lines[self.from_line], text=text[: self.from_row - 1] + text[self.from_row + 0 :]
        )
        cursor_row = self.from_row - 1

    def undo(self):
        global cursor_row, cursor_line
        text = lines[self.from_line].text
        undone_text = text[: self.from_row - 1] + self.content + text[self.from_row - 1 :]
        lines[self.from_line] = replace(lines[self.from_line], text=undone_text)
        cursor_row = self.from_row
        cursor_line = self.from_line


@dataclass
class BackspaceNewlineAction:
    from_line: int
    from_row: int
    first_line: Line
    second_line: Line

    def do(self):
        global cursor_row, cursor_line
        text_a = lines[self.from_line - 1].text
        text_b = lines[self.from_line].text
        lines[self.from_line - 1] = replace(lines[self.from_line - 1], text=text_a + text_b)
        lines.pop(self.from_line)
        cursor_line = self.from_line - 1
        cursor_row = len(text_a)

    def undo(self):
        global cursor_row, cursor_line
        lines[self.from_line - 1] = self.first_line
        lines.insert(self.from_line, self.second_line)
        cursor_row = self.from_row
        cursor_line = self.from_line


# Function to handle doing actions where we check undoing the action leaves us in the initial state
def do_action_checked(action):
    initial_state = (lines, cursor_line, cursor_row)
    initial_state_saved = pickle.dumps(initial_state)

    action.do()
    action.undo()

    new_state = (lines, cursor_line, cursor_row)
    new_state_saved = pickle.dumps(new_state)

    assert new_state_saved == initial_state_saved

    action.do()


# Initialize editor state
REGULAR_FONT_AND_SIZE = "Roboto-Regular.ttf", 16
cursor_line = 1
cursor_row = "Life is Mineplex".find("Mineplex")
maybe_saved_cursor_row = None

lines = [Line("Roboto-Bold.ttf", 40, "", 0)]
actions = [
    TypingAction(0, 0, "Answers questions"),
    NewlineAction(0, len("Answers questions"), "Answers questions", False),
    TypingAction(1, 0, "What is the dataset? We do"),
    NewlineAction(1, len("What is the dataset? We do"), "What is the dataset? We do", True),
    TypingAction(2, 0, "not know. But whatis life?"),
    NewlineAction(2, len("not know. But what is life?"), "not know. But whatis life?", False),
    TypingAction(3, 0, ""),
    NewlineAction(3, len(""), "", False),
    TypingAction(4, 0, "Life is MineplexXX"),
    BackspaceCharacterAction(4, len("Life is MineplexXX"), "X"),
    BackspaceCharacterAction(4, len("Life is MineplexX"), "X"),
    NewlineAction(4, len("Life is Mineplex"), "Life is Mineplex", True),
    TypingAction(5, 0, "Life is Super Paintball"),
]
for action in actions:
    action.do()

# Run main loop
def main():
    global cursor_line, cursor_row, maybe_saved_cursor_row
    running = True
    clock = pygame.time.Clock()
    while running:
        # Debug test
        assert all(isinstance(l, Line) for l in lines)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Backspace
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                if len(lines) > cursor_line and cursor_row > 0:
                    actions.append(
                        BackspaceCharacterAction(
                            from_line=cursor_line, from_row=cursor_row, content=lines[cursor_line].text[cursor_row - 1]
                        )
                    )
                    do_action_checked(actions[-1])
                elif len(lines) > cursor_line and cursor_row == 0 and cursor_line > 0:
                    actions.append(
                        BackspaceNewlineAction(
                            from_line=cursor_line,
                            from_row=cursor_row,
                            first_line=lines[cursor_line - 1],
                            second_line=lines[cursor_line],
                        )
                    )
                    do_action_checked(actions[-1])

            # Typing
            if event.type == pygame.KEYDOWN:
                # Save pressed keys
                pressed_scancodes = list(pygame.key.get_pressed())
                pressed_mods_int = pygame.key.get_mods()
                pressed_control = bool(pressed_mods_int & pygame.KMOD_CTRL)
                pressed_shift = bool(pressed_mods_int & pygame.KMOD_SHIFT)
                pressed_alt = bool(pressed_mods_int & pygame.KMOD_ALT)
                pressed_caps = pressed_scancodes[pygame.KSCAN_CAPSLOCK]

                # Debug print
                if event.unicode:
                    print(f"Pressed key {repr(event.unicode)} ({ord(event.unicode)}) with keycode {event.key}")
                else:
                    print(f"Pressed empty key with keycode {event.key}")

                # Enter
                if event.key == pygame.K_RETURN:
                    actions.append(
                        NewlineAction(
                            from_line=cursor_line,
                            from_row=cursor_row,
                            line_content=lines[cursor_line].text,
                            big_new_line=pressed_shift,
                        )
                    )
                    do_action_checked(actions[-1])

                # Tab
                elif event.key == pygame.K_TAB:
                    pass

                # Normal typing
                elif event.unicode and event.unicode in DISPLAYABLE_CHARACTERS:
                    actions.append(TypingAction(insert_line=cursor_line, insert_row=cursor_row, content=event.unicode))
                    do_action_checked(actions[-1])

                # Movement left
                elif pressed_control and event.key == pygame.K_h:
                    maybe_saved_cursor_row = None
                    can_move_left = (cursor_row - 1) in range(len(lines[cursor_line].text) + 1)
                    if can_move_left:
                        cursor_row -= 1

                # Movement right
                elif pressed_control and event.key == pygame.K_l:
                    maybe_saved_cursor_row = None
                    can_move_right = (cursor_row + 1) in range(len(lines[cursor_line].text) + 1)
                    if can_move_right:
                        cursor_row += 1

                # Movement down
                elif pressed_control and event.key == pygame.K_j:
                    can_move_down = (cursor_line + 1) in range(len(lines))
                    if can_move_down:
                        cursor_line += 1
                        if maybe_saved_cursor_row is None:
                            maybe_saved_cursor_row = cursor_row
                        else:
                            cursor_row = maybe_saved_cursor_row
                        cursor_row = min(cursor_row, len(lines[cursor_line].text))
                        assert cursor_row in range(len(lines[cursor_line].text) + 1)

                # Movement up
                elif pressed_control and event.key == pygame.K_k:
                    can_move_up = (cursor_line - 1) in range(len(lines))
                    if can_move_up:
                        cursor_line -= 1
                        if maybe_saved_cursor_row is None:
                            maybe_saved_cursor_row = cursor_row
                        else:
                            cursor_row = maybe_saved_cursor_row
                        cursor_row = min(cursor_row, len(lines[cursor_line].text))
                        assert cursor_row in range(len(lines[cursor_line].text) + 1)

                # Undo
                elif pressed_control and event.key == pygame.K_z:
                    if actions:
                        last_action = actions.pop()
                        last_action.undo()

            # Screen resizing
            elif event.type == pygame.WINDOWRESIZED:
                screen_width = event.x
                screen_height = event.y

        # Paint background
        screen.fill((255, 255, 255))

        # Draw text
        def draw_line(line):
            global y
            pygame.draw.rect(screen, (240, 140, 130), (LEFT_PADDING - 10, y - line.space_before, 3, line.space_before))
            real_font = pygame.font.Font(line.font, line.size)
            screen.blit(real_font.render(line.text, True, (55, 53, 47)), (LEFT_PADDING, y))
            y += real_font.size(line.text)[1]

        global y
        y = 200
        line_index = 0
        for line in lines:
            y += line.space_before

            # Draw cursor
            if line_index == cursor_line:
                pygame.draw.rect(
                    screen,
                    (55, 53, 47),
                    (
                        LEFT_PADDING + pygame.font.Font(line.font, line.size).size(line.text[:cursor_row])[0] - 1,
                        y + 1,
                        1,
                        pygame.font.Font(line.font, line.size).size("X")[1] - 2,
                    ),
                )

            # Draw line
            draw_line(line)
            line_index += 1

        # Refresh screen
        pygame.display.flip()

        clock.tick(60)


main()
