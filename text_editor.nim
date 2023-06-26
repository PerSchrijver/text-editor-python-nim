#!/home/per/.nimble/bin/nim r
import random

import std/tables
import std/sequtils
import std/sugar
import std/strutils

import sdl2
import sdl2/ttf


type SDLException = object of Defect

template sdlFailIf(condition: typed, reason: string) =
  if condition: raise SDLException.newException(
    reason & ", SDL error " & $getError()
  )

const
  WindowWidth = 1280
  WindowHeight = 720

  TextHeight = 16

type
  LineItemKind* = enum
    Textual
    PythonCode

  LineIndex = distinct cint

  LineItem* = object
    index: LineIndex
    content: string
    indent: cint
    case kind*: LineItemKind
      of Textual:
        size: int
      of PythonCode:
        discard

  AutoCompleteSnippet = distinct seq[string]

type Globals* = object
  lines: seq[LineItem]
  current_line: LineIndex
  known_completions: Table[string, AutoCompleteSnippet]
  autocomplete_options: seq[string]
  autocomplete_enabled: bool

proc drawText(renderer: RendererPtr, font: FontPtr, text: cstring, color: Color,
    x: cint, y: cint) =
  if text.len == 0:
    return
  assert not renderer.isNil
  assert not font.isNil
  assert not text.isNil
  let
    surface = ttf.renderTextBlended(font, text, color)
  sdlFailIf(surface.isNil):
    "Font rendering"
  assert not surface.isNil
  echo $surface.h
  echo text

  echo $cast[uint64](renderer)
  echo $renderer.setDrawColor(0, 0, 0)

  let
    texture = renderer.createTextureFromSurface(surface)

  surface.freeSurface
  defer: texture.destroy

  var r = rect(
    x,
    y,
    surface.w,
    surface.h
  )
  renderer.copy texture, nil, addr r

proc draw(globals: Globals, renderer: RendererPtr, font: FontPtr, dt: float32) =
  renderer.setDrawColor 255, 255, 255, 255 # black
  renderer.clear()

  var
    w: cint = 0
    h: cint = 0
  discard ttf.sizeText(font, "X", addr w, addr h)

  var y: cint = 10
  for t in globals.lines:
    case t.kind:
    of Textual:
      renderer.drawText(font, cstring(t.content), color(55, 53, 47, 0), 10 + w *
          t.indent, y)
      y += h
    of PythonCode:
      renderer.drawText(font, cstring(t.content), color(55, 53, 247, 0), 10 +
          w * t.indent, y)
      y += h

  if globals.autocomplete_enabled:
    var y: cint = 10
    for option in globals.autocomplete_options[0..min(5, globals.autocomplete_options.len - 1)]:
      renderer.drawText(font, cstring($option), color(55, 53, 47, 0), 400, y)
      y += h

  renderer.present()

type
  InputKind* = enum
    CtrlH
    CtrlJ
    CtrlK
    CtrlL
    CtrlSpace
    CtrlBackspace
    DisplayableCharacter
    Return
    Tab
    ShiftTab
    Backspace
    None

  Input* = object
    case kind*: InputKind:
    of DisplayableCharacter:
      character: char
    else:
      nil

proc updateAutocomplete(globals: var Globals, term: string) =
  globals.autocomplete_options = globals.known_completions.keys.toSeq.filter(x => x.contains(term))

proc enableAutocomplete(globals: var Globals, term: string) =
  globals.autocomplete_enabled = true
  globals.updateAutocomplete(term)

proc completeAutocomplete(globals: var Globals) =
  assert globals.autocomplete_enabled
  if globals.known_completions.len == 0:
    return
  let option = globals.known_completions[globals.autocomplete_options[0]]
  globals.lines[cast[cint](globals.current_line)].content = cast[seq[string]](option).join("-")
  globals.updateAutocomplete("")
  globals.autocomplete_enabled = false

proc handleLineItemInput(globals: var Globals, line_item: var LineItem,
    input: Input) =
  case input.kind:
    of DisplayableCharacter:
      line_item.content.add(input.character)
      globals.updateAutocomplete(line_item.content)
    of Tab:
      if globals.autocomplete_enabled:
        globals.completeAutocomplete()
      else:
        line_item.indent += 2
    of ShiftTab:
      if line_item.indent >= 2:
        line_item.indent -= 2
      else:
        line_item.indent = 0
    of CtrlSpace:
      globals.enableAutocomplete(line_item.content)
    of Backspace:
      if line_item.content.len > 0:
        line_item.content = line_item.content[.. ^2]
        globals.updateAutocomplete(line_item.content)
    else: discard

proc handleInput(globals: var Globals, input: Input) =
  globals.handleLineItemInput(globals.lines[cast[cint](globals.current_line)], input)

func isDisplayableAsciiCharacterMap(): array[0..127, bool] =
  for c in " qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890!@#$%^&*()_+~`-=[]\\;',./{}|:\"<>?":
    result[cast[cint](c)] = true

func toInput(c: char): Input =
  const table = isDisplayableAsciiCharacterMap()
  if cast[cint](c) in 0..127 and table[cast[cint](c)]:
    Input(kind: DisplayableCharacter, character: c)
  else:
    Input(kind: None)

func toInput(key: Scancode, mod_state: Keymod): Input =
  let
    MOD_SHIFT = KMOD_LSHIFT or KMOD_RSHIFT
    MOD_CTRL = KMOD_LCTRL or KMOD_RCTRL

  # Only shift and no mod
  if (mod_state and not MOD_SHIFT) == 0:
    case key:
      of SDL_SCANCODE_RETURN: Input(kind: Return)
      of SDL_SCANCODE_BACKSPACE: Input(kind: Backspace)
      of SDL_SCANCODE_TAB:
        if (mod_state and MOD_SHIFT) == 0:
          Input(kind: Tab)
        else:
          Input(kind: ShiftTab)
      else: Input(kind: None)

  # Ctrl and only ctrl
  elif (mod_state and MOD_CTRL) != 0 and (mod_state and not MOD_CTRL) == 0:
    case key
    of SDL_SCANCODE_H: Input(kind: CtrlH)
    of SDL_SCANCODE_J: Input(kind: CtrlJ)
    of SDL_SCANCODE_K: Input(kind: CtrlK)
    of SDL_SCANCODE_L: Input(kind: CtrlL)
    of SDL_SCANCODE_SPACE: Input(kind: CtrlSpace)
    of SDL_SCANCODE_BACKSPACE: Input(kind: CtrlBackspace)
    else: Input(kind: None)

  else:
    Input(kind: None)


proc main =
  sdlFailIf(not sdl2.init(INIT_VIDEO or INIT_TIMER or INIT_EVENTS)):
    "SDL2 initialization failed"
  defer: sdl2.quit()

  let window = createWindow(
    title = "Text Editor Biatch",
    x = SDL_WINDOWPOS_CENTERED,
    y = SDL_WINDOWPOS_CENTERED,
    w = WindowWidth,
    h = WindowHeight,
    flags = SDL_WINDOW_SHOWN or SDL_WINDOW_RESIZABLE
  )

  sdlFailIf window.isNil: "window could not be created"
  defer: window.destroy()

  let renderer = createRenderer(
    window = window,
    index = -1,
    flags = Renderer_Accelerated or Renderer_PresentVsync or Renderer_TargetTexture
  )
  sdlFailIf renderer.isNil: "renderer could not be created"
  defer: renderer.destroy()

  sdlFailIf(not ttfInit()): "SDL_TTF initialization failed"
  defer: ttfQuit()

  let font = ttf.openFont("Roboto-Regular.ttf", TextHeight)
  sdlFailIf font.isNil: "font could not be created"

  var
    running = true

    globals = Globals(
      lines: @[
        LineItem(kind: PythonCode, content: "yo", index: LineIndex 0),
        LineItem(kind: Textual, content: "", index: LineIndex 1, size: 40),
        LineItem(kind: PythonCode, content: "gehoe", index: LineIndex 2)
      ],
      current_line: LineIndex 1,
      known_completions: {"print": AutoCompleteSnippet @["print"],
          "map": AutoCompleteSnippet @["X", ".map(", "X", "=>", "X", ")"]}.toTable
    )

    dt: float32

    counter: uint64
    previousCounter: uint64

  for term in "printer! pineapple prone_to_failure exit uppercase".splitWhitespace:
    globals.known_completions[term] = AutoCompleteSnippet @[term]
  globals.known_completions["if"] = AutocompleteSnippet @["if", "???", "then", "???", "else","???(Unit)"]

  counter = getPerformanceCounter()

  while running:
    previousCounter = counter
    counter = getPerformanceCounter()

    dt = (counter - previousCounter).float / getPerformanceFrequency().float

    var event = defaultEvent

    while pollEvent(event):
      case event.kind
      of QuitEvent:
        running = false
        break

      of TextInput:
        globals.handleInput(toInput(event.evTextInput.text[0]))
        echo $toInput(event.evTextInput.text[0])


      of KeyDown:
        globals.handleInput(toInput(event.evKeyboard.keysym.scancode, cast[
            Keymod](event.evKeyboard.keysym.modstate)))
        echo $toInput(event.evKeyboard.keysym.scancode, cast[Keymod](
            event.evKeyboard.keysym.modstate))

      else:
        discard

    globals.draw(renderer, font, dt)

main()
