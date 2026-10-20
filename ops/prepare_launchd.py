#!/usr/bin/env python3
"""Generate launchd candidates without installing or starting them."""
from __future__ import annotations

import argparse
from pathlib import Path
import plistlib


def definitions(app: Path, archive: Path, binary: Path, prefix: str, port: int):
    logs = app/'logs'
    common = {'EnvironmentVariables': {'HOME': str(Path.home()),
               'PATH': '/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
              'WorkingDirectory': str(app)}
    commands = {
        'serve': [str(binary),'--home',str(archive),'--config',str(archive/'config.toml'),'serve'],
        'vue-dev': ['/usr/local/bin/flox','activate','--dir',str(app),'--',
                    'npm','run','dev','--','--port',str(port),'--strictPort'],
        'import-emlx': ['/usr/local/bin/flox','activate','--dir',str(app),'--',
                        '/bin/bash',str(app/'ops/run-mail.sh'),'import'],
        'purge-trash': ['/usr/local/bin/flox','activate','--dir',str(app),'--',
                       '/bin/bash',str(app/'ops/run-mail.sh'),'purge-trash','--apply'],
    }
    for name, command in commands.items():
        definition = {**common,'Label': prefix+'.'+name,'ProgramArguments':command,
                      'StandardOutPath':str(logs/(name+'.log')),
                      'StandardErrorPath':str(logs/(name+'.log'))}
        if name in ('serve','vue-dev'):
            definition.update(KeepAlive=True,RunAtLoad=True)
        else:
            definition['StartInterval'] = 900 if name == 'import-emlx' else 1800
        yield name, definition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prefix',default='com.msgvault')
    parser.add_argument('--frontend-port',type=int,default=3000)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.app_dir/'logs').mkdir(parents=True,exist_ok=True)
    for name, definition in definitions(args.app_dir.resolve(),args.archive.resolve(),
                                         args.binary.resolve(),args.prefix,args.frontend_port):
        with (args.output/(args.prefix+'.'+name+'.plist')).open('wb') as handle:
            plistlib.dump(definition,handle)


if __name__ == '__main__':
    main()
