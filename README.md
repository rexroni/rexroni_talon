# rexroni's Talon repository

This is my talon repository, where I put things which I hope will be generally
useful for other people who also use talon.  Ideally, each part is easy to
understand and is usable without any of the other parts.

Install this repo into your `~/.talon/user` directory like this:

```sh
cd ~/.talon/user
git clone https://github.com/rexroni/rexroni_talon
```

The current list of features is:

* **Zsh completion recognition**: continuously register zsh completion with talon
* **Language Server Integration**: speak symbols or tab-completions from your IDE

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

### Zsh Configuration

All you should have to do is `source` the `setup.zsh` file in your zsh:

```sh
source ~/.talon/user/rexroni_talon/zsh-completion-server/setup.zsh
```

This will have the following effects:

- It will start a completion server served over a unix socket in the
  `rexroni_talon/zsh-completion-server/sock` directory (created automatically).

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

## Language Server Integration

In your editor, you can say "complete \<a tab completion option\>" or "symbol
\<a symbol in the document\>" and Talon will emit the appropriate symbol.  It
works by wrapping the language server process in a wrapper that peeks at the
Language Server Protocol messages and informs Talon about editor information.

### Prerequisites

- Currently, the implementation uses unix sockets, so you'll need to be on
  Linux or Mac

- You'll need an editor which uses the Language Server Protocol (LSP) for its
  language integrations.  LSP is popular, so you're probably in luck.

### Editor configuration:

- **Vim**:

  1. There are various LSP plugins for Vim.  Instructions below are for
     [vim-lsc](https://github.com/natebosch/vim-lsc).  Install the plugin
     however you install vim plugins.

  1. Install a language server like `pyls` (for python) or `clangd` (for C/C++)
     through your system's package manager.

  1. Configure `vim-lsp` in your `~/.vimrc`:

     ```vim
     " Wrap each language server with wrap-langserv.
     let g:lsc_server_commands = {
      \ 'python': $HOME.'/.talon/user/rexroni_talon/wrap-langserv pyls',
      \ 'c': $HOME.'/.talon/user/rexroni_talon/wrap-langserv clangd',
      \ }

     " Trigger autocomplete after a single letter when it is not triggered by
     " anything else:
     let g:lsc_autocomplete_length = 1

     """""""
     " If you do not want the usual features of a language server but only want
     " it for the Talon integration, you can turn off most of the features.
     " I highly recommend reading through the vim-lsp documentation before
     " long, but this will get you started:
     let g:lsc_auto_map = v:false
     set completeopt-=preview
     let g:lsc_reference_highlights = v:false
     let g:lsc_enable_diagnostics = v:false
     """""""
     ```

- **Sublime**:

  1. Install the `LSP` plugin for Sublime.

  1. Install a language server like `pyls` (for python) or `clangd` (for C/C++)
     through your system's package manager.

  1. Enable a couple of plugins, like `pyls` and `clangd`, via the
     `LSP: Enable Langauge Server Globally` command in the Command Pallette.

  1. Visit your `Preferences: LSP Settings`.

  1. In the user settings, set the `clients` for each client to have a new
     `command` setting that wraps each language server with `wrap-langserv`:

     ```json
     {
         "clients":
         {
             "clangd":
             {
                 "command": ["~/.talon/user/rexroni_talon/wrap-langserv", "clangd"],
                 "enabled": true
             },
             "pyls":
             {
                 "command": ["~/.talon/user/rexroni_talon/wrap-langserv", "pyls"],
                 "enabled": true
             }
         }
     }
     ```

### First steps

1. With your editor, open a file named `test.py`.  This will activate the
   `pyls` language server.

1. Type the following characters: `test_string = "Asdf".`  The `.` will trigger
   a completion request, which `wrap-langserv` will detect and tell Talon
   about.

1. After the pop-up appears with completion options in your IDE, say
   "complete lower".  Talon will type out "lower" for you.

1. Finish the line with a pair of parens `()` and hit enter to start a new
   line.

1. Now say "symbol test string".  Talon will type out "test\_string" for you,
   a symbol that it recognizes from within the document (note that a document
   symbol is different than a token; there will be tokens in the file which
   `pyls` does not report as symbols).

## License

The files in `zsh-completion-server/fn/` were copied with modification from the
[zsh4humans](https://github.com/romkatv/zsh4humans) project, which is under the
MIT license (Copyright (c) 2020 Roman Perepelitsa).  The modifications from
those original files and all additional files in this repository are public
domain, as described by the [Unlicense](https://unlicense.org).
