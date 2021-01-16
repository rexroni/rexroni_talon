# rexroni's Talon repository

This is my talon repository, where I put things which I hope will be generally
useful for other people who also use talon.  Ideally, each part is easy to
understand and is usable without any of the other parts.

The current list of features is:

* *Zsh completion recognition*: continuously register zsh completion with talon

## Zsh completion recognition

You can speak a word that zsh would let you complete, and talon will type that
word.  After every talon phrase, talon will request a fresh list of completions
from zsh for the next phrase.

### Prerequisites

- Currently, the implementation uses unix sockets, so you'll need to be on
  Linux or Mac

- Make sure you are using `zsh` as your shell.  Zsh has a lot of canned
  configurations.  If you are new to it, I recommend the `grml` package, which
  offers a like-bash-but-better experience with basically no effort.

### Configuration

All you should have to do is `source` the `setup.zsh` file in your zsh:

```sh
source ~/.talon/user/rexroni-talon/zsh-completion-server/setup.zsh
```

This will have the following effects:

- It will start a completion server served over a unix socket in the
  `zsh-completion-server/sock` directory (created automatically).

- It will set your terminal emulator's window title to `zsh:$PID:$PWD`,
  which the `zsh.py` talon module will use to identify which completion
  server to talk to.  When a command is running, the completion server will
  be inactive and `setup.zsh` will replace the title with the running
  command.

### First steps

1. With a zsh window focused, try saying "identify yourself".  If the zsh talon
   app is active, it will type `zsh.talon`.  If it doesn't work, you'll have to
   troubleshoot.  It is triggered by a window title starting with `zsh:`.

1. Completions for an empty command line are ignored (there's too many).  But
   90% of CLI commands fall into a few categories.  Try saying: "cd space".

1. Then, try saying a subdirectory name.  Some basic pronunciation rules are:
   - you should always pronounce file extensions, like "dot pie" for `.py`
   - you can ignore any of `.` or `-` or `_` when you pronounce the file,
     though if you have ambiguous completion options, you chose to pronounce
     them
   - if there is a partial word being completed, you can either pronounce the
     rest of the word, or the entire word.  Whichever is easiest.
   - you can say "show" or type `ctrl-g` to ask `zsh` to show you the
     completions available at any time

1. Say "cancel" to make talon type a `ctrl-c`.

1. Now say "git space" (as its own phrase), then say "commit space", then say
   "dash dash", and then say "amend".  The result should be
   `git commit --amend`.  That's about all there is to it!

## License

The files in `zsh-completion-server/fn/` were copied with modification from the
[zsh4humans](https://github.com/romkatv/zsh4humans) project, which is under the
MIT license (Copyright (c) 2020 Roman Perepelitsa).  The modifications from
those original files and all additional files in this repository are public
domain, as described by the [Unlicense](https://unlicense.org).
