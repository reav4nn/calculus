# calculus

a gtk4/libadwaita calculator for arch linux. glassmorphism styling, dark/light mode support, history panel, keyboard shortcuts.

## dependencies

```
sudo pacman -S python gtk4 libadwaita python-gobject
```

## run

```
python3 calculus.py
```

## keyboard shortcuts

| key | action |
|-----|--------|
| 0-9 | numbers |
| + - * / | operators |
| enter | calculate |
| escape | clear |
| backspace | delete last |
| ctrl+h | toggle history |
| % | percent |
| ( ) | parentheses |

## install system-wide (optional)

```
sudo mkdir -p /opt/calculus
sudo cp calculus.py style.css /opt/calculus/
sudo cp io.github.calculus.desktop /usr/share/applications/
```

## license

gpl-3.0
