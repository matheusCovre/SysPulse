import sys, tty, termios, select

old = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

print("Press arrows. 'q' to quit.")
try:
    while True:
        if select.select([sys.stdin], [], [], 0.1)[0]:
            char = sys.stdin.read(1)
            if char == '\x1b':
                rest = sys.stdin.read(2)
                print(f"Arrow/Esc: {repr(char + rest)}")
            else:
                print(f"Char: {repr(char)}")
                if char == 'q': break
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
