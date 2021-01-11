# shell.talon
os: linux
# Is this better in zsh.py?  It seems to be required there and optional here.
# title: /^zsh:/
app: zsh
-
# tag(): user.file_manager
# tag(): user.git
identify yourself: insert("zsh.talon")
is shell active: key(escape)

list files: insert("ls\n")
# cd: "cd "

cancel: key(ctrl-c)

say <user.text> slash:
    insert(user.text)
    insert("/")

<user.shell_command>:
    insert(user.shell_command)

<user.zsh_completion>:
    insert(user.zsh_completion)

show: key(ctrl-g)

above: insert("../")

# scroll up:
#   key(shift-pageup)
# scroll down:
#   key(shift-pagedown)
# run last:
#   key(up)
#   key(enter)
# rerun <user.shell_command>:
#   key(ctrl-r)
#   insert(user.shell_command)
# rerun search:
#   key(ctrl-r)

# action(edit.page_down):
#   key(shift-pagedown)
# action(edit.page_up):
#   key(shift-pageup)
# action(edit.paste):
#   key(ctrl-shift-v)
# action(edit.copy):
#   key(ctrl-shift-c)
#


# kill all:
#   key(ctrl-c)
#
# # XXX - these are specific to certain terminals only and should move into their
# # own <term name>.talon file
# action(edit.find):
#   key(ctrl-shift-f)
# action(edit.word_left):
#   key(ctrl-w-left)
# action(edit.word_right):
#   key(ctrl-w-right)
# action(app.tab_open):
#   key(ctrl-shift-t)
# action(app.tab_close):
#   key(ctrl-shift-w)
# action(app.tab_next):
#   key(ctrl-pagedown)
# action(app.tab_previous):
#   key(ctrl-pageup)
# action(app.window_open):
#   key(ctrl-shift-n)
# go tab <number>:
#   key("alt-{number}")
