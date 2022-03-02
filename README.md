A command-line tool for converting predicates into simplified CNF or DNF.

Converts to CNF by default.

Interprets the order of precedence: ['~', '&&', '||', '=>']

Interprets the following as logic symbols: ['&&', '||', '~', '(', ')', '=>']. Everything else is interpreted as a
term. Spaces are ignored.

Usage: main.py sentence [dnf]

Usage example 1:
```
> main.py 'a => b && c' dnf
~a || (b && c)
```

Usage example 2:
```
> main.py 'a => b && ~c'
(~a || ~c) && (~a || b)
```
