# Keyboard shortcut registry

One catalog is the single list of command keys. The binding, the shortcuts dialog, and each key
hint read it, so a key that works is a key that the user can find.

## Catalog

Each entry SHOULD have: a typed `id`, `keys`, optional `aliases`, a lazy `label` (so it follows the
locale), a `group` for the dialog, a `scope`, and flags for where the key works (text fields,
dialogs, editors). An entry for a gesture that no hook binds (`mod+click`, `space+drag`) MAY be a
reference entry that only the dialog shows.

- A component MUST bind a command through the one hook, by id. It MUST NOT add a raw `keydown`
  listener or call a hotkey library directly for a command.
- The shortcuts dialog MUST be generated from the catalog.
- Tooltips and menu items SHOULD show the key from the catalog, not a hard-coded string.
- A shortcut SHOULD be discoverable: show it in tooltips and menus, and open the dialog with `?`
  or `mod+/`.

## Conflicts

Write a unit test over the catalog:

1. Normalize each binding: lowercase, one order of modifiers, `mod` resolved for each platform.
2. Compare `keys` and every alias of each entry with every other entry in the same scope.
3. If the app has presets (for example editor key maps), check each preset.
4. Fail on a duplicate. Also fail on a bound id that is not in the catalog.

Search for listeners outside the catalog before you add a key. A conflict test sees only the
catalog.

## Where a key works

- A key MUST be active only while its surface owns the keys: its scope or mode is active, and no
  dialog, tour, or menu is open over it.
- In an input, a textarea, or a contenteditable, a command key MUST be ignored by default. An entry
  MAY opt in (for example `mod+Enter` to send).
- A key event during IME composition (`isComposing`, or `keyCode 229`) MUST be ignored.
- Space and Enter on a focused button, link, or menu item MUST keep their native action.
- Call `preventDefault` only when the command runs. Otherwise the key keeps its default action.
- Decide repeat for each command. A one-shot command MUST ignore `event.repeat`. A nudge or a zoom
  MAY repeat.

## Keys and platforms

- Show `mod` as Command on macOS and Ctrl elsewhere. A server render cannot know the platform.
  Render the non-Mac form, and update it after mount.
- For a character shortcut (`[`, `/`, `=`), match `event.key`. For a positional shortcut (WASD),
  match `event.code`.
- For a letter with `mod`, fall back to `event.code` when `event.key` is not a Latin letter. On a
  Cyrillic or Greek layout, `event.key` is the local letter.
- Match an Alt or Option shortcut by `event.code`. On macOS, Option changes `event.key` (Option+S
  gives "ß").
- Shift changes `event.key`. Give `mod+=` an alias for `mod+shift+=` and for the `+` key.
- You MUST NOT bind keys that the browser keeps: `mod+w`, `mod+shift+w`, `mod+t`, `mod+shift+t`,
  `mod+n`, `mod+shift+n`, `ctrl+tab`, `ctrl+shift+tab`, and Command+Q. You MUST NOT bind Tab or
  Shift+Tab as a command, because they move focus. You SHOULD NOT bind operating system keys such
  as Command+H, Command+M, and Command+Space.
- If the app takes over page zoom (`mod+=`, `mod+-`) on a canvas, it MUST take it over in the
  canvas text fields too. Otherwise the browser zooms the page.

## Listener phase

- Bind at the document in the bubble phase. A focused widget can then stop a key it uses.
- A capture-phase listener takes keys from every widget. Use it only for a modal surface (a
  full-screen editor), and remove it on unmount.

## Local keys

A key that works only inside one focused widget stays in the widget and follows its ARIA pattern:
Escape closes an editor, arrow keys move in a list box, Enter commits a field. A key that the user
learns as a command goes in the catalog.
