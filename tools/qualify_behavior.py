"""Execute portable native behavior checks and a negative mutation in isolated scratch copies.

Small reproducible engineering probes, not a real-project semantic benchmark. No network,
package installation or production files. The JSON output includes missing-tool conditions.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('qualification_core', ROOT/'src/agent_repo_kit/core.py')
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


def execute(root, name, argv, output):
    local = root/'.probe-logs'/output.name
    local.mkdir(parents=True, exist_ok=True)
    result = kit.run_check(root, {'name': name, 'argv': argv, 'timeout': 30}, local)
    source = root/result['log']
    destination = output/source.name
    shutil.copyfile(source, destination)
    result['log'] = str(destination)
    return result


def qualify(destination):
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    samples = [
        ('C', 'cc', 'probe.c', '#include <assert.h>\nint accept(int n) { return n >= 0 && n < 8; }\nint main(void) { assert(accept(0)); assert(accept(7)); assert(!accept(8)); assert(!accept(-1)); return 0; }\n', 'n < 8', 'n <= 8'),
        ('C++', 'c++', 'probe.cpp', '#include <stdexcept>\nint accept(int n) { return n >= 0 && n < 8; }\nint main() { if (!accept(0) || !accept(7) || accept(8) || accept(-1)) throw std::runtime_error("boundary mismatch"); return 0; }\n', 'n < 8', 'n <= 8'),
        ('Java', 'javac', 'Probe.java', 'class Probe { static boolean accept(int n) { return n >= 0 && n < 8; } public static void main(String[] args) { if (!accept(0) || !accept(7) || accept(8) || accept(-1)) throw new AssertionError("boundary mismatch"); } }\n', 'n < 8', 'n <= 8'),
    ]
    for stack, compiler, filename, source, original, mutation in samples:
        available = shutil.which(compiler)
        if not available or stack == 'Java' and not shutil.which('java'):
            results.append({'stack': stack, 'status': 'NOT_RUN', 'reason': f'{compiler}/runtime unavailable; no packages installed'})
            continue
        with tempfile.TemporaryDirectory(prefix='ark-behavior-probe-') as temporary:
            root = Path(temporary)
            path = root/filename
            path.write_text(source, encoding='utf-8')
            version = subprocess.run([available, '-version' if stack == 'Java' else '--version'], capture_output=True, text=True, timeout=15)
            binary = 'probe.exe' if sys.platform == 'win32' else 'probe'
            compile_argv = [available, filename] if stack == 'Java' else [available, filename, '-o', binary]
            test_argv = [shutil.which('java'), '-cp', '.', 'Probe'] if stack == 'Java' else [str(root/binary)]
            runs = []
            for phase, content in [('original', source), ('mutation', source.replace(original, mutation)), ('restored', source)]:
                path.write_text(content, encoding='utf-8')
                log = destination/stack.replace('+','p')/phase
                log.mkdir(parents=True, exist_ok=True)
                build = execute(root, 'build', compile_argv, log)
                test = execute(root, 'behavior', test_argv, log) if build['status'] == 'PASS' else {'status':'NOT_RUN','reason':'Compilation failed'}
                runs.append({'phase':phase,'source_sha256':kit.digest(path.read_bytes()),'build':build,'test':test})
            okay = all(r['build']['status']=='PASS' for r in runs) and [r['test']['status'] for r in runs] == ['PASS','FAIL','PASS']
            results.append({'stack':stack, 'status':'PASS' if okay else 'FAIL', 'compiler': available,
                            'version':(version.stdout+version.stderr).splitlines()[:1], 'runs':runs,
                            'meaning':'Observed boundary regression detection only; not exhaustive stack/project qualification'})
    relay = ROOT/'examples/config-relay'
    with tempfile.TemporaryDirectory(prefix='ark-relay-probe-') as temporary:
        root = Path(temporary)/'relay'
        shutil.copytree(relay,root)
        log=destination/'python'; log.mkdir(exist_ok=True)
        argv=[sys.executable,'-m','unittest','discover','-s','tests','-v']
        original=execute(root,'original',argv,log)
        path=root/'relay.py'; before=path.read_text(encoding='utf-8')
        path.write_text(before.replace("self.latest[device] = sequence", "self.latest[device] = sequence\n        if not self.transport.online: return 'offline'"),encoding='utf-8')
        negative=execute(root,'mutation',argv,log)
        path.write_text(before,encoding='utf-8')
        restored=execute(root,'restored',argv,log)
        results.append({'stack':'Python','status':'PASS' if [r['status'] for r in (original,negative,restored)]==['PASS','FAIL','PASS'] else 'FAIL',
                        'runs':[original,negative,restored], 'meaning':'Six actual cross-module relay tests; mutation changes offline acceptance semantics'})
    report={'kit_version':kit.VERSION,'platform':sys.platform,'results':results,
            'status':'FAIL' if any(r['status']=='FAIL' for r in results) else 'PENDING' if any(r['status']=='NOT_RUN' for r in results) else 'PASS',
            'meaning':'Actual bounded native probes, not model semantic quality, project coverage or production compatibility'}
    (destination/'qualification.json').write_text(kit.dump(report),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=qualify(args.output.resolve())
    print(json.dumps({'status':result['status'],'results':[{k:r[k] for k in ('stack','status')} for r in result['results']]}))
    raise SystemExit(1 if result['status']=='FAIL' else 2 if result['status']=='PENDING' else 0)
