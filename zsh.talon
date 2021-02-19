# zsh.talon
app: zsh
-
identify yourself: insert("zsh.talon")

list files: insert("ls\n")
git status: insert("git status\n")

cancel: key(ctrl-c)

show: key(ctrl-g)

<user.shell_command>:
    insert(user.shell_command)

^<user.zsh_completion>:
    insert(user.zsh_completion)

above: insert("../")
