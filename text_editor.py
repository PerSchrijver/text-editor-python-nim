#!/usr/bin/env python3.10
from dataclasses import dataclass, replace
import pickle
import string
import time
from typing import List, Optional, Tuple
import pygame
from rich import print as pp

# Initialize performance necessary constants
DISPLAYABLE_CHARACTERS = set(string.printable) - set("\t\r\n\x0b\x0c")

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
    items: List["LineItem"]
    space_before: int

    def text_length(self) -> int:
        return Line.text_length_of_items(self.items)

    def character_at(self, row: int) -> "str":
        return self.items_after_row(row)[0].content[0]

    def items_before_and_after_row(self, row: int) -> Tuple[List["LineItem"], List["LineItem"]]:
        first = []
        second = []
        i = None
        for i, item in enumerate(self.items):
            if row == len(item.content):
                first.append(item)
                break
            if row > len(item.content):
                first.append(item)
                row -= len(item.content)
            else:
                first.append(replace(item, content=item.content[:row]))
                second.append(replace(item, content=item.content[row:]))
                break
        if i is None:
            second = []
        else:
            second += self.items[i + 1 :]
        return first, second

    def items_before_row(self, row: int) -> List["LineItem"]:
        return self.items_before_and_after_row(row)[0]

    def items_after_row(self, row: int) -> List["LineItem"]:
        return self.items_before_and_after_row(row)[1]

    def splitted_for_newline(self, row: int, big_newline: bool) -> Tuple["Line", "Line"]:
        first = replace(self, items=self.items_before_row(row))
        if big_newline:
            second = Line(*REGULAR_FONT_AND_SIZE, self.items_after_row(row) or [LineItem("")], 8)
        else:
            second = Line(*REGULAR_FONT_AND_SIZE, self.items_after_row(row) or [LineItem("")], 0)
        return first, second

    @staticmethod
    def item_at_row(self, row: int) -> Optional[Tuple["LineItem", int]]:
        for item in enumerate(self.items):
            if row >= len(item.content):
                row -= len(item.content)
            else:
                return item, row
        return None

    @staticmethod
    def text_length_of_items(items: List["LineItem"]) -> int:
        return sum(len(item.content) for item in items)

    @staticmethod
    def with_text_added_to_items(items: List["LineItem"], text: str) -> List["LineItem"]:
        assert len(items)
        return Line.merge_two_list_item_lists(items[:-1], [replace(items[-1], content=items[-1].content + text)])

    @staticmethod
    def merge_two_list_item_lists(first: List["LineItem"], second: List["LineItem"]) -> List["LineItem"]:
        can_merge = len(first) and len(second) and type(first[-1]) == type(second[0])
        if can_merge:
            merged = replace(first[-1], content=first[-1].content + second[0].content)
            new_items = first[:-1] + [merged] + second[1:]
        else:
            new_items = first + second
        return new_items


@dataclass(frozen=True)
class LineItem:
    content: str

    def with_text_inserted(self, row: int, text: str) -> "Self":
        return replace(self, content=self.content[:row] + text + self.content[row:])

    def with_text_uninserted(self, row: int, text: str) -> "Self":
        return replace(self, content=self.content[:row] + self.content[len(text) + row :])


@dataclass(frozen=True)
class ColoredLineItem(LineItem):
    color: Tuple[int, int, int]


# Actions
@dataclass
class TypingAction:
    insert_line: int
    insert_row: int
    content: str

    def do(self):
        global cursor_row, cursor_line
        line = lines[self.insert_line]
        lines[self.insert_line] = replace(
            line,
            items=Line.merge_two_list_item_lists(
                Line.with_text_added_to_items(line.items_before_row(cursor_row), self.content),
                line.items_after_row(cursor_row),
            ),
        )
        cursor_row = self.insert_row + len(self.content)
        cursor_line = self.insert_line

    def undo(self):
        global cursor_row, cursor_line
        line = lines[self.insert_line]
        undone_items = Line.merge_two_list_item_lists(
            line.items_before_row(self.insert_row), line.items_after_row(len(self.content) + self.insert_row)
        )
        lines[self.insert_line] = replace(lines[self.insert_line], items=undone_items)
        cursor_row = self.insert_row
        cursor_line = self.insert_line


@dataclass
class NewlineAction:
    from_line: int
    from_row: int
    line_content: List["LineItem"]
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
        lines[self.from_line] = replace(lines[self.from_line], items=self.line_content)
        lines.pop(self.from_line + 1)
        cursor_row = self.from_row
        cursor_line = self.from_line


@dataclass
class BackspaceCharacterAction:
    from_line: int
    from_row: int
    content: str

    def do(self):
        global cursor_row, cursor_line
        line = lines[self.from_line]
        lines[self.from_line] = replace(
            line,
            items=Line.merge_two_list_item_lists(
                line.items_before_row(self.from_row - 1), line.items_after_row(self.from_row + 0)
            ),
        )
        cursor_row = self.from_row - 1
        cursor_line = self.from_line

    def undo(self):
        global cursor_row, cursor_line
        line = lines[self.from_line]
        lines[self.from_line] = replace(
            lines[self.from_line],
            items=Line.merge_two_list_item_lists(
                Line.with_text_added_to_items(line.items_before_row(self.from_row - 1), self.content),
                line.items_after_row(self.from_row - 1),
            ),
        )
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
        first, second = lines[self.from_line - 1].items, lines[self.from_line].items
        can_merge = len(first) and len(second) and type(first[-1]) == type(second[0])
        if can_merge:
            merged = replace(first[-1], content=first[-1].content + second[0].content)
            new_items = first[:-1] + [merged] + second[1:]
        else:
            new_items = first + second

        lines[self.from_line - 1] = replace(lines[self.from_line - 1], items=new_items)
        lines.pop(self.from_line)
        cursor_line = self.from_line - 1
        cursor_row = Line.text_length_of_items(first)

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

    if new_state_saved != initial_state_saved:
        print("Previous actions:")
        for a in actions:
            pp(a)
        pp(f"While doing {action}, doing and undoing resulted in a difference")
        print("Initial state:")
        pp(pickle.loads(initial_state_saved))
        print("New state:")
        pp(pickle.loads(new_state_saved))
        exit()

    redo_actions.clear()

    action.do()


# Initialize editor state
REGULAR_FONT_AND_SIZE = "Roboto-Regular.ttf", 16
cursor_line = 0
cursor_row = 0
maybe_saved_cursor_row = None

lines = [Line("Roboto-Bold.ttf", 40, [LineItem("")], 0)]
actions = [
    TypingAction(0, 0, "Answers questions"),
    NewlineAction(0, len("Answers questions"), [LineItem("Answers questions")], False),
    TypingAction(1, 0, "What is the dataset?X"),
    BackspaceCharacterAction(1, len("What is the dataset?X"), "X"),
    TypingAction(1, len("What is the dataset?"), " We do"),
    NewlineAction(1, len("What is the dataset? We do"), [LineItem("What is the dataset? We do")], True),
    TypingAction(2, 0, "not know. But what is life?"),
    NewlineAction(2, len("not know. But what is life?"), [LineItem("not know. But what is life?")], False),
    TypingAction(3, 0, ""),
    NewlineAction(3, len(""), [LineItem("")], False),
    TypingAction(4, 0, "Life is MineplexXX"),
    BackspaceCharacterAction(4, len("Life is MineplexXX"), "X"),
    BackspaceCharacterAction(4, len("Life is MineplexX"), "X"),
    NewlineAction(4, len("Life is Mineplex"), [LineItem("Life is Mineplex")], True),
    TypingAction(5, 0, "Life is Super Paintball"),
]
redo_actions = []
for action in actions:
    do_action_checked(action)
    assert all(isinstance(l, Line) for l in lines)
    assert all(all(isinstance(i, LineItem) for i in l.items) for l in lines)

# Run main loop
def main():
    global cursor_line, cursor_row, maybe_saved_cursor_row
    running = True
    clock = pygame.time.Clock()
    while running:
        # Debug test
        assert all(isinstance(l, Line) for l in lines)
        assert all(all(isinstance(i, LineItem) for i in l.items) for l in lines)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Backspace
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                if len(lines) > cursor_line and cursor_row > 0:
                    actions.append(
                        BackspaceCharacterAction(
                            from_line=cursor_line,
                            from_row=cursor_row,
                            content=lines[cursor_line].character_at(cursor_row - 1),
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

                print("Pressed alt", pressed_alt)

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
                            line_content=lines[cursor_line].items,
                            big_new_line=pressed_shift,
                        )
                    )
                    do_action_checked(actions[-1])

                # Tab
                elif event.key == pygame.K_TAB:
                    pass

                # Normal typing
                elif (not pressed_alt) and event.unicode in DISPLAYABLE_CHARACTERS:
                    actions.append(TypingAction(insert_line=cursor_line, insert_row=cursor_row, content=event.unicode))
                    do_action_checked(actions[-1])

                # Movement left
                elif pressed_control and event.key == pygame.K_h:
                    maybe_saved_cursor_row = None
                    can_move_left = (cursor_row - 1) in range(lines[cursor_line].text_length() + 1)
                    if can_move_left:
                        cursor_row -= 1

                # Movement right
                elif pressed_control and event.key == pygame.K_l:
                    maybe_saved_cursor_row = None
                    can_move_right = (cursor_row + 1) in range(lines[cursor_line].text_length() + 1)
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
                        cursor_row = min(cursor_row, lines[cursor_line].text_length())
                        assert cursor_row in range(lines[cursor_line].text_length() + 1)

                # Movement up
                elif pressed_control and event.key == pygame.K_k:
                    can_move_up = (cursor_line - 1) in range(len(lines))
                    if can_move_up:
                        cursor_line -= 1
                        if maybe_saved_cursor_row is None:
                            maybe_saved_cursor_row = cursor_row
                        else:
                            cursor_row = maybe_saved_cursor_row
                        cursor_row = min(cursor_row, lines[cursor_line].text_length())
                        assert cursor_row in range(lines[cursor_line].text_length() + 1)

                # Undo
                elif pressed_control and event.key == pygame.K_z:
                    if actions:
                        last_action = actions.pop()
                        last_action.undo()
                        redo_actions.append(last_action)

                # Redo
                elif pressed_control and event.key == pygame.K_y:
                    if redo_actions:
                        last_action = redo_actions.pop()
                        last_action.do()
                        actions.append(last_action)

                # Crash on arrow use
                elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                    screen.fill((240, 45, 45))
                    screen.blit(
                        pygame.font.Font("Roboto-Bold.ttf", 70).render("studeren = hydrateren", True, (55, 53, 47)),
                        (100, 100),
                    )
                    pygame.display.flip()
                    time.sleep(2)

                elif pressed_alt and event.key in (pygame.K_h, pygame.K_j, pygame.K_k, pygame.K_l):
                    screen.fill((240, 45, 45))
                    screen.blit(
                        pygame.font.Font("Roboto-Bold.ttf", 70).render("gebruik de pijltjes", True, (55, 53, 47)),
                        (100, 100),
                    )
                    pygame.display.flip()
                    time.sleep(2)

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
            x = LEFT_PADDING
            for item in line.items:
                screen.blit(real_font.render(item.content, True, (55, 53, 47)), (x, y))
                x += real_font.size(item.content)[0]
            y += real_font.size("X")[1]

        global y
        y = 200
        line_index = 0
        for line in lines:
            y += line.space_before

            # Draw cursor
            if line_index == cursor_line:
                cursor_x = LEFT_PADDING
                for item in line.items_before_row(cursor_row):
                    cursor_x += pygame.font.Font(line.font, line.size).size(item.content)[0]
                pygame.draw.rect(
                    screen,
                    (55, 53, 47),
                    (
                        cursor_x - 1,
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
