#!/home/per/.nimble/bin/nim r
import random

import sdl2
import sdl2/ttf

const
  WindowWidth = 1280
  WindowHeight = 720

  TextHeight = 16

type
  LineItemKind* = enum
    Textual
    PythonCode

  LineItem* = object
    content: string
    indent: cint
    case kind*: LineItemKind
      of Textual:
        size: int
      of PythonCode:
        discard


type Globals* = object
  lines: seq[LineItem]

proc drawText(renderer: RendererPtr, font: FontPtr, text: cstring, color: Color,
    x: cint, y: cint) =
  let
    surface = ttf.renderTextBlended(font, text, color)
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
      renderer.drawText(font, cstring(t.content), color(55, 53, 47, 0), 10 + w * t.indent, y)
      y += h
    of PythonCode:
      renderer.drawText(font, cstring(t.content), color(55, 53, 247, 0), 10 + w * t.indent, y)
      y += h

  renderer.present()


type SDLException = object of Defect

template sdlFailIf(condition: typed, reason: string) =
  if condition: raise SDLException.newException(
    reason & ", SDL error " & $getError()
  )

type
  InputKind* = enum
    CtrlH
    CtrlJ
    CtrlK
    CtrlL
    CtrlSpace
    DisplayableCharacter
    Return
    Tab
    ShiftTab
    None

  Input* = object
    case kind*: InputKind:
    of DisplayableCharacter:
      character: char
    else:
      nil

proc handleLineItemInput(globals: var Globals, line_item: var LineItem, input: Input) =
  case input.kind:
    of DisplayableCharacter:
      line_item.content.add(input.character)
    of Tab:
      line_item.indent += 2
    of ShiftTab:
      if line_item.indent >= 2:
        line_item.indent -= 2
      else:
        line_item.indent = 0
    else: discard

proc handleInput(globals: var Globals, input: Input) =
  globals.handleLineItemInput(globals.lines[^1], input)

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

  let font = ttf.openFont("/home/per/.local/share/fonts/Hack Regular Nerd Font Complete.ttf", TextHeight)
  sdlFailIf font.isNil: "font could not be created"

  var
    running = true

    globals = Globals(lines: @[LineItem(kind: PythonCode, content: "yo"),
        LineItem(kind: Textual, content: "yo", size: 40), LineItem(
        kind: PythonCode, content: "gehoe")])

    dt: float32

    counter: uint64
    previousCounter: uint64

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