r"""
Finder Makefile help interface.

(!!) Please don't run this script directly. Use 'make help' instead.

PROTIP: If you just want to know how to use it, not how it works, see
`'make help ON=help'`.

This script implements a help system that extracts documentation directly
from the Makefile itself. The Makefile is annotated so that comments placed
immediately above a target definition are treated as that target's description.
This is modeled after Python docstrings.

Lines beginning with `':variables:'` declare which variables the target accepts.

Lines beginning with `'(!!)'` are warnings and are emboldened. The `'(!!)'` is
underlined, too.

Lines beginning with `'PROTIP:'` are tips and the `'PROTIP:'` keyword is
emboldened and underlined.

Lines beginning with `'NOTE:'` are notes and the `'NOTE:'` keyword is
emboldened and underlined.

\`...\` segments and lines beginning with `':'` are considered code and
emboldened.

Blank lines reset the comment/variable buffer so that only contiguous
annotations are associated with the next target.

Here's an example:

:    NAME=world
:    
:    # This rule prints a greeting.
:    #
:    # Use the variable NAME to choose who to greet. It defaults to 'world'.
:    #
:    # :variables: NAME
:    greet:
:        echo Hello $(NAME)!

This is rendered as:

:    make greet [NAME=...]
:    
:        This rule prints a greeting.
:        
:        Use the variable NAME to choose who to greet. It defaults to 'world'.

It uses Pydoc to get help on Python scripts.
"""
import re
import sys
import os
import io
import textwrap
import webbrowser
import pydoc
from contextlib import contextmanager
from pathlib import Path

CODE_RE = re.compile(r"(?<!\\)`(.*?)`")

class Just:
    """Namespace of helpers for justifying text."""
    @staticmethod
    def space_between(words, total_width):
        if len(words) == 1:
            return words[0].ljust(total_width)
        
        # Calculate characters and spaces needed
        total_chars = sum(len(w) for w in words)
        remaining_spaces = total_width - total_chars
        num_gaps = len(words) - 1
        
        # Evenly divide spaces
        base_space = remaining_spaces // num_gaps
        extra_spaces = remaining_spaces % num_gaps
        
        result = ""
        for i, word in enumerate(words[:-1]):
            # Distribute any leftover modulo spaces from left to right
            spaces_to_add = base_space + (1 if i < extra_spaces else 0)
            result += word + (" " * spaces_to_add)
            
        result += words[-1] # Append the final item
        return result

    @staticmethod
    def vertical(text, height):
        return text + ("\n" * (height - len(text.split('\n'))))

def b(text):
    return "".join(f"{c}\b{c}" for c in text)

def u(text):
    return "".join(f"_\b{c}" for c in text)

def bu(text):
    return "".join(f"_\b{c}\b{c}" for c in text)

class Pager:
    """
    A wrapper around `pydoc.pager` that redirects `sys.stdout` to an 
    `io.StringIO` upon entering the context manager, and captures
    the output before paging it using `pydoc.pager` upon exit with
    a custom header.
    """
    
    def __enter__(self):
        self.f = io.StringIO()
        self.o = sys.stdout
        self.heading = "Pager"
        sys.stdout = self.f
        return self
    
    def escape(self):
        @contextmanager
        def escape_type(parent):
            sys.stdout = parent.o
            try:
                yield
            finally:
                sys.stdout = parent.f
        
        return escape_type(self)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.o
        
        if exc_type or exc_val or exc_tb:
            return
        
        try:
            sz = os.get_terminal_size()
        except:
            sz = os.terminal_size((80, 25))
        
        txt = Just.space_between(
            [u(self.heading), "Finder Makefile help interface", u(self.heading)],
            sz.columns + (len(self.heading) * 4) # adjust for overstrike
        )
        
        txt += "\n" + ("\n" if os.name != "nt" else "")
        txt += self.f.getvalue().rstrip()
        txt = Just.vertical(txt, sz.lines - (1 if os.name == "nt" else 0))
        
        pydoc.pager(txt, title=self.heading)

def ident(txt, lvl=1):
    return textwrap.indent(txt, "    " * lvl, predicate=lambda x: True)

def ddent(txt):
    return "\n".join(
        [" ".join(line.split()) for line in textwrap.dedent(txt).split("\n")]
    )

def fmt_docln(line):
    line = CODE_RE.sub(lambda m: b(m[1]), line)
    
    if line.startswith("(!!)"):
        line = bu("(!!)") + b(line.removeprefix("(!!)"))
    elif line.startswith("PROTIP:"):
        line = bu("PROTIP:") + line.removeprefix("PROTIP:")
    elif line.startswith("NOTE:"):
        line = bu("NOTE:") + line.removeprefix("NOTE:")
    elif line.startswith(":"):
        line = b(line[1:])
    
    return line

def parse_makefile(filepath="Makefile"):
    """
    This parser collects the metadata stored in the Makefile into a dictionary
    of targets, each mapped to its description and variable list.
    """
    target_pattern = re.compile(r"^([a-zA-Z0-9_-][a-zA-Z0-9_.-]*)\s*:(?!:=).*$")
    targets = {}
    comments = []
    variables = []
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Error: {filepath} not found.")

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                line = line.removeprefix("#")
                if line.startswith(" "):
                    line = line[1:]
                
                if line.startswith(":variables:"):
                    variables.extend(
                        line.removeprefix(":variables:").strip().split()
                    )
                else:
                    comments.append(fmt_docln(line))
            elif match := target_pattern.match(line):
                name = match.group(1)
                targets[name] = (
                    "\n".join(comments).strip() or "(no description)",
                    sorted(variables)
                )
                comments = []
                variables = []
            elif not line:
                comments = []
                variables = []
                
    return dict(sorted(targets.items(), key=lambda x: x[0].lower()))

def main():
    # Accept the target name as a command-line argument
    target = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    if target == "web":
        webbrowser.open("https://finder-locw.onrender.com/docs/dev")
        return

    targets = parse_makefile()

    with Pager() as p:
        if target:
            if target in targets:
                desc, vars_ = targets[target]
                p.heading = f"make {target}"
                print(ident(ddent(f"""\
                    {b(f"make {target}")} {" ".join(map(lambda x: b("[") + 
                                           bu(x) + b("=...]"), vars_))}""")))
                print()
                print(ident(desc, 2))
            elif target.endswith(".py"):
                if "env" not in sys.executable:
                    with p.escape():
                        try:
                            input(ddent(f"""\
                                The virtual environment does not seem to be \
                                activated.
                                Some Python scripts may fail to load.
                                Run {"'ienv'" if sys.platform == "win32" else 
                                "'. ienv'"} to activate it.
                                If that fails, run 'make deps' first.
                                Press Enter to continue without activating or \
                                Ctrl-C to quit...""") + " ")
                        except KeyboardInterrupt:
                            print()
                            print("Goodbye, traveller!")
                            sys.exit(0)
                
                p.heading = target
                
                # Prevent any ModuleNotFoundErrors from not being able
                # to find modules
                sys.path.append(str(Path(target).parent))
                
                with p.escape():
                    x = ident(pydoc.render_doc(pydoc.importfile(target)))
                
                print(x, end="")
            else:
                raise FileNotFoundError(f"Topic '{target}' not found.")
        else:
            p.heading = "Makefile"
            print(ident(b("make [target]")))
            print(ident(ddent(f"""
                Finder Makefile. This is just a handy automation Makefile to save you from
                running a bunch of commands.

                {u("Available rules:")}"""), 2))
            for t, (desc, _) in targets.items():
                print(ident(f"- {b(t.ljust(25))} {desc.split("\n")[0]}", 3))
            print(ident(ddent("""
                Run 'make help ON=<target_name>' for focused info.
                Run 'make help ON=<python_file.py>' for info about the specified script.
                Run 'make help ON=help' for more info about this help interface.
                Run 'make help ON=web' for help online.

                NOTE: Some rules need a Makefile.secret, so it's a good idea to create one
                immediately. You can either write your own or interactively create one using
                'make Makefile.secret'."""), 2))

if __name__ == "__main__":
    main()