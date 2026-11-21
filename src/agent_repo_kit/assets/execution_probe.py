"""Execute a Python test command and retain actual assertion line observations.

This adapter does not prove assertion semantics. It preserves failed/uncalled assertions,
and supports Python script, -m and the common exec(open(...).read()) command form.
"""
import ast
import json
import os
from pathlib import Path
import runpy
import sys
import traceback


def main():
    output, root, encoded, roots = sys.argv[1:5]
    args = json.loads(encoded)
    root = Path(root).resolve()
    test_roots = [root / value for value in json.loads(roots)]
    assertions, seen, failed, active = {}, set(), set(), {}
    inline_path = root / '@command.py'

    def source(filename):
        path = Path(filename)
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        if path == inline_path and path in assertions:
            return path
        if not path.is_relative_to(root) or not any(path == t or path.is_relative_to(t) for t in test_roots):
            return None
        if path not in assertions:
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
                assertions[path] = {node.lineno: node.end_lineno for node in ast.walk(tree)
                                    if isinstance(node, ast.Assert) or isinstance(node, ast.Expr)
                                    and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                                    and node.value.func.attr.startswith('assert')}
            except (OSError, SyntaxError, UnicodeError):
                assertions[path] = {}
        return path

    # Enumerate before execution so skipped/never-called assertions remain observable.
    for directory in test_roots:
        for path in ([directory] if directory.is_file() else directory.rglob('*.py')):
            source(str(path))

    def trace(frame, event, arg):
        path = source(frame.f_code.co_filename)
        if path is None:
            return None
        if event == 'line':
            line = frame.f_lineno
            matches = [start for start, end in assertions[path].items() if start <= line <= end]
            if matches:
                key = (path, matches[0])
                seen.add(key)
                active[id(frame)] = key
            else:
                active.pop(id(frame), None)
        elif event == 'exception' and id(frame) in active:
            failed.add(active[id(frame)])
        elif event == 'return':
            active.pop(id(frame), None)
        return trace

    status = 0
    sys.path.insert(0, str(Path.cwd()))
    try:
        sys.settrace(trace)
        if args[0] == '-m':
            sys.argv = args[1:]
            runpy.run_module(args[1], run_name='__main__', alter_sys=True)
        elif args[0] == '-c':
            sys.argv = ['-c', *args[2:]]
            code, filename = args[1], str(inline_path)
            # Preserve the original exec command's globals and argv, while assigning
            # the actual test filename to the code object used for line observations.
            tree = ast.parse(code)
            if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                call = tree.body[0].value
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'exec' and len(call.args) == 1:
                    read = call.args[0]
                    if isinstance(read, ast.Call) and isinstance(read.func, ast.Attribute) and read.func.attr == 'read' and not read.args:
                        opening = read.func.value
                        if isinstance(opening, ast.Call) and isinstance(opening.func, ast.Name) and opening.func.id == 'open' and opening.args and isinstance(opening.args[0], ast.Constant) and isinstance(opening.args[0].value, str):
                            filename = str(Path(opening.args[0].value).resolve())
                            code = Path(filename).read_text(encoding='utf-8')
            if filename == str(inline_path):
                assertions[inline_path] = {node.lineno: node.end_lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)}
            exec(compile(code, filename, 'exec'), {'__name__': '__main__', '__builtins__': __builtins__})
        elif args and not args[0].startswith('-'):
            sys.argv = args
            sys.path[0] = str(Path(args[0]).resolve().parent)
            runpy.run_path(args[0], run_name='__main__')
        else:
            raise ValueError('Unsupported Python flags; use an explicit test report adapter')
    except SystemExit as exc:
        status = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException:
        traceback.print_exc()
        status = 1
    finally:
        sys.settrace(None)
        cases = [{'id': path.relative_to(root).as_posix() + ':L' + str(line),
                  'status': 'FAIL' if (path, line) in failed else 'PASS' if (path, line) in seen else 'NOT_RUN'}
                 for path, lines in sorted(assertions.items()) for line in sorted(lines)]
        Path(output).write_text(json.dumps({'schema_version': 1, 'run_id': os.environ['ARK_RUN_ID'],
                                           'adapter': 'python-assertion-trace', 'cases': cases}), encoding='utf-8')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
