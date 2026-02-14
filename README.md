# calculus

a gtk4/libadwaita calculator. glassmorphism styling, dark/light mode support, history panel, keyboard shortcuts.

## dependencies

works on any linux distro with gtk4 and libadwaita 1.4+.

| distro | install |
|--------|---------|
| arch | `sudo pacman -S python gtk4 libadwaita python-gobject` |
| fedora 39+ | `sudo dnf install python3 gtk4 libadwaita python3-gobject` |
| ubuntu 23.10+ | `sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` |
| opensuse tw | `sudo zypper install python3 python3-gobject gtk4 libadwaita typelib-1_0-Adw-1` |

> **note:** requires libadwaita 1.4 or newer. ubuntu 22.04 and debian 12 ship older versions and won't work. on non-gnome desktops, make sure `adwaita-icon-theme` is installed.

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
