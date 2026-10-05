"""Check owned-directory failure paths without writing outside the repository.

--native-output is an explicit Linux-only smoke test of the PostgreSQL tempdir
exception; it starts no database and removes the native directory before exit.
"""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import lab_r2_common as common


def failure_cases():
    parent=common.confined('.lab-runs','.lab-runs/r2a')
    parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cleanup-r2d-',dir=parent) as temporary:
        fixture=Path(temporary).resolve()
        assert fixture.is_relative_to(parent)
        for case in ('chmod','bad-mode','resolve','remove','log','stop'):
            output=fixture/(case+'.json')
            owned=fixture/(case+'-owned')
            owned.mkdir()
            smoke=common.LabRun('cleanup-synthetic',output,['scripts/verify_lab_r2_cleanup.py'])
            workspace=None
            original_chmod=Path.chmod
            original_stat=Path.stat
            original_resolve=Path.resolve
            original_remove=shutil.rmtree
            def chmod(path,*args,**kwargs):
                if path==owned:
                    if case=='chmod':
                        raise PermissionError('synthetic chmod failure')
                    return None
                return original_chmod(path,*args,**kwargs)
            def stat(path,*args,**kwargs):
                result=original_stat(path,*args,**kwargs)
                if path==owned and case=='bad-mode':
                    import os
                    result=os.stat_result((0o40755,*tuple(result)[1:]))
                return result
            def resolve(path,*args,**kwargs):
                if path==owned and case=='resolve':
                    raise OSError('synthetic resolve failure')
                return original_resolve(path,*args,**kwargs)
            def remove(path,*args,**kwargs):
                if Path(path)==owned and case=='remove':
                    raise PermissionError('synthetic remove failure')
                return original_remove(path,*args,**kwargs)
            try:
                with redirect_stdout(io.StringIO()), patch.object(common.shutil,'rmtree',side_effect=remove):
                    with smoke:
                        workspace=smoke.workspace
                        if case in ('chmod','bad-mode','resolve'):
                            # Simulate a native filesystem with a fixture INSIDE the repo.
                            # ROOT is changed only during this method, then restored before
                            # cleanup/output path checks. No external directory is created.
                            with patch.object(common,'ROOT',fixture/'simulated-repository'), \
                                 patch.object(common,'linux_required'), \
                                 patch.object(common.tempfile,'mkdtemp',return_value=str(owned)), \
                                 patch.object(Path,'chmod',chmod), patch.object(Path,'stat',stat), \
                                 patch.object(Path,'resolve',resolve):
                                smoke.native_directory('fixture-','synthetic permission failure')
                        else:
                            smoke.native_dirs.append(owned)
                            if case=='log':
                                smoke.logs.append(('missing',fixture/'missing.log',io.StringIO()))
                            if case=='stop':
                                smoke.processes.append(object())
                                def fail_stop(process):
                                    raise RuntimeError('synthetic process stop failure')
                                smoke.stop=fail_stop
                saved=json.loads(output.read_text(encoding='utf-8'))
                assert smoke.exit_code==1 and saved['status']=='error',case
                if case in ('chmod','bad-mode','resolve'):
                    assert smoke.native_dirs==[owned]
                    assert saved['native_directories'][0]['verified'] is False
                    assert saved['cleanup']['completed'] and not owned.exists()
                    assert not workspace.exists()
                elif case=='log':
                    assert saved['native_directories_removed'] and not owned.exists()
                    assert not saved['cleanup']['completed']
                else:
                    assert not saved['native_directories_removed']
                    assert not saved['cleanup']['completed'] and owned.exists()
                try:
                    common.LabRun('no-overwrite',output,[])
                except FileExistsError:
                    pass
                else:
                    raise AssertionError('Existing result could be overwritten')
            finally:
                if workspace and workspace.exists():
                    original_remove(common.confined('.lab-runs',workspace))
    print('PASS: 6 synthetic cleanup failures, ownership retained before verification, error status, no overwrite; repository-only fixtures')


def native_smoke(output):
    common.linux_required()
    with common.LabRun('native-cleanup-smoke',output,['scripts/verify_lab_r2_cleanup.py']) as run:
        directory=run.native_directory('dk-r2-smoke-','Explicit Linux native permission/cleanup smoke; no server')
        assert directory.stat().st_mode & 0o777 == 0o700
        assert not directory.resolve().is_relative_to(common.ROOT)
        (directory/'owned-marker').write_text('cleanup smoke',encoding='utf-8')
    saved=json.loads(run.output.read_text(encoding='utf-8'))
    assert run.exit_code==0 and saved['cleanup']['completed']
    assert saved['native_directories_removed'] and not directory.exists()
    print('PASS: native 0700 directory removed; no database or service started')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-output',type=Path)
    args=parser.parse_args()
    if args.native_output:
        native_smoke(args.native_output)
    else:
        failure_cases()


if __name__=='__main__':
    main()
