#!/usr/bin/env python3.10
from dataclasses import dataclass, replace
import string
from typing import NamedTuple
import pygame

# Initialize performance necessary constants
DISPLAYABLE_CHARACTERS = set(string.printable) - set(" \t\r\n")

# Initialize screen
WIDTH, HEIGHT = 1280, 720
LEFT_PADDING = 400
MIDDLE_WIDTH = WIDTH - LEFT_PADDING * 2
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.init()

# Enable key repeating
pygame.key.set_repeat(300, 1000 // 20)

# Editor classes
@dataclass(frozen=True)
class Line:
    font: pygame.font.Font
    size: int
    text: str


# Initialize editor state
REGULAR_FONT_AND_SIZE = "Roboto-Regular.ttf", 16
lines = [
    Line("Roboto-Bold.ttf", 40, "Answers questions"),
    Line(*REGULAR_FONT_AND_SIZE, "What is the dataset? We do"),
    Line(*REGULAR_FONT_AND_SIZE, "no know. But what is life?"),
    Line(*REGULAR_FONT_AND_SIZE, ""),
    Line(*REGULAR_FONT_AND_SIZE, "Life is Mineplex"),
]
cursor_line = 1
cursor_row = "Life is Mineplex".find("Mineplex")

print([name for name in dir(pygame) if getattr(pygame, name) == 57])
# exit()

# Run main loop
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
                text = lines[cursor_line].text
                lines[cursor_line] = replace(lines[cursor_line], text=text[: cursor_row - 1] + text[cursor_row + 0 :])
                cursor_row -= 1
            elif len(lines) > cursor_line and cursor_row == 0 and cursor_line > 0:
                line = lines[cursor_line]
                text_a = lines[cursor_line - 1].text
                text_b = lines[cursor_line].text
                lines[cursor_line - 1] = replace(lines[cursor_line - 1], text=text_a + text_b)
                lines.pop(cursor_line)
                cursor_line -= 1
                cursor_row = len(text_a)

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
                text = lines[cursor_line].text
                lines[cursor_line] = replace(lines[cursor_line], text=text[:cursor_row])
                if pressed_shift:
                    lines.insert(cursor_line + 1, Line(*REGULAR_FONT_AND_SIZE, text[cursor_row:]))
                    lines.insert(cursor_line + 1, Line(REGULAR_FONT_AND_SIZE[0], 8, ""))
                    cursor_line += 1
                else:
                    lines.insert(cursor_line + 1, Line(*REGULAR_FONT_AND_SIZE, text[cursor_row:]))
                cursor_line += 1
                cursor_row = 0

            # Tab
            elif event.key == pygame.K_TAB:
                pass

            # Normal typing
            elif event.unicode and event.unicode in DISPLAYABLE_CHARACTERS:
                text = lines[cursor_line].text
                lines[cursor_line] = replace(
                    lines[cursor_line], text=text[:cursor_row] + event.unicode + text[cursor_row:]
                )
                cursor_row += 1

    # Paint background
    screen.fill((255, 255, 255))

    # Draw text
    def draw_line(font, size, text):
        global y
        real_font = pygame.font.Font(font, size)
        screen.blit(real_font.render(text, True, (55, 53, 47)), (LEFT_PADDING, y))
        y += real_font.size(text)[1]

    y = 200
    line_index = 0
    for l in lines:
        # Draw cursor
        if line_index == cursor_line:
            pygame.draw.rect(
                screen,
                (55, 53, 47),
                (
                    LEFT_PADDING + pygame.font.Font(l.font, l.size).size(l.text[:cursor_row])[0] - 1,
                    y + 1,
                    1,
                    pygame.font.Font(l.font, l.size).size("X")[1] - 2,
                ),
            )

        # Draw line
        draw_line(l.font, l.size, l.text)
        line_index += 1

    # Refresh screen
    pygame.display.flip()

    clock.tick(60)