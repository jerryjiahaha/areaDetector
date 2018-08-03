#!/usr/bin/env python3
# Fuck shell/bash so I use python

"""
Script to configure epics modules automatically.
Generate CONFIG_SITE.* EPICS_BASE.* SUPPORT* files
"""

from collections import namedtuple
from pathlib import Path
from functools import reduce
import os
import re

CONFIG_PATTERN_KV = re.compile('^[\t ]*([-_a-zA-Z0-9]+)? *= *(\S+)')
ClassConfig = namedtuple('ClassConfig', 'fname content')

class EpicsConfig:
    _CONFIGS = []
    @staticmethod
    def __init__(fname, content, module=''):
        filedir = os.path.dirname(os.path.abspath(__file__))
        realfname = os.path.join(filedir, module, "configure", fname)
        EpicsConfig._CONFIGS.append(ClassConfig(realfname, content))
    @staticmethod
    def dump(envs, write=False):
        for c in EpicsConfig._CONFIGS:
            outfile = c.fname.format_map(envs)
            outcontent = c.content.format_map(envs)
            print('fname:', outfile)
            if write:
                with Path(outfile).open('w') as f:
                    f.write(outcontent)
            else:
                print('content:', outcontent) 


epics_env_config_defaults = {
    'BASE_PATH': "/opt/epics",
    'BASE_SUPPORT_PATH': "/opt/epics/modules",
    'EPICS_HOST_ARCH': 'linux-x86_64',
    'AD_PATH': os.path.dirname(os.path.abspath(__file__)),
}

_alias = {
    'EPICS_BASE': 'BASE_PATH',
    'SUPPORT': 'BASE_SUPPORT_PATH',
}

base_support = """
EPICS_BASE={BASE_PATH}
SUPPORT={BASE_SUPPORT_PATH}
"""

_ad_depends = {'asyn', 'autosave', 'sscan', 'busy',
    'devIocStats', 'alive', 'calc', 'seq',
}

module_alias = {
    # module dir name: module support name
    'seq': 'SNCSEQ',
}

# depend_path format example: `ASYN=$(SUPPORT)/asyn`
_mod_map = {
    module_alias.get(mod, mod): os.path.join("{SUPPORT}", mod) \
    for mod in _ad_depends
}
_depend_path="\n".join([ f"{K.upper()}={V}" for K, V in _mod_map.items() ]) + "\n"

_ad_modules = ("ADSimDetector",
    "ADViewers",
    "ADAndor",
    "ADPvCam",
    "ADPluginEdge",
    "NDDriverStdArrays",
)

ad_modules_def = """
AREA_DETECTOR={AD_PATH}
""" + "\n".join([
    f"""{mod.upper()}={os.path.join('$(AREA_DETECTOR)', mod)}""" for mod in ('ADCore', 'ADSupport',)])

files_to_copy = ('RELEASE_SUPPORT.local', 'RELEASE_LIBS.local', )

def extract_default_config(filename):
    """Parse files with <K>=<V> info
    """
    src_dir = os.path.dirname(os.path.abspath(__file__))
    filename = Path(src_dir).joinpath(filename)
    lines = filename.open().readlines()
    ret = {}
    for line in lines:
        try:
            k, v = line.split('=')
            ret[k.strip()] = v.strip()
        except ValueError:
            pass
    return ret

_external_libs = extract_default_config(os.path.join('configure', 'EXAMPLE_CONFIG_SITE.local'))
_external_libs.update({
    'XML2_EXTERNAL': 'YES',
    'XML2_INCLUDE': '/usr/include/libxml2', # TODO use pkg-config or xml2-config
})


def render_n_copy(filename, content, write=False):
    """Copy EXAMPLE_<filename> to <filename>,
    and inject config content into file
    """
    src_dir = os.path.dirname(os.path.abspath(__file__))
    p = Path(src_dir).joinpath('configure', f"EXAMPLE_{filename}")
    lines = p.open().readlines()
    output = ""
    for line in lines:
        if CONFIG_PATTERN_KV.match(line):
            output += '#' + line
        else:
            output += line
    # inject content before include
    find = output.find('-include')
    if find >= 0:
        output = output[:find] + f"""
        \n{content}
        \n""" + output[find:] + "\n"
    else:
        output = f"""
        \n{output}
        \n{content}
        \n"""
    if write:
        filename = Path(src_dir).joinpath('configure', filename)
        print("fname:", filename)
        with filename.open(mode='w') as f:
            f.write(output)
    else:
        print(f"{filename} content\n: {output}")

# XXX must be executed under epics-moduels root dir
if __name__ == '__main__':
    from os import getenv
    # These variable could be overrided by local script
    epics_env_config = {
        k: getenv(k) or v for k, v in epics_env_config_defaults.items()
    }
    epics_env_config.update({
        a: epics_env_config[n] for a, n in _alias.items()
    })
    # e.g. ASYN=<support>/asyn
    depend_path = _depend_path
    ad_modules = _ad_modules
    external_libs = {}
    # NOTE not tested yet
    try:
        from config_site_local import *
    except ImportError as e:
        pass
    _external_libs.update(external_libs)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    print("epics_env_config:", epics_env_config)
    print("depend_path:", depend_path)
    print("ad_modules:", ad_modules)
    print("external_libs:", _external_libs)

    ad_modules_def += "\n\n" + "\n".join([
        f"""{mod.upper()}={os.path.join('$(AREA_DETECTOR)', mod)}""" \
            for mod in ad_modules ]) + "\n"
    print("ad_modules_def:", ad_modules_def)

#    depend_path = depend_path.format_map(epics_env_config)
    areadetector_envs = ""
    # add BASE, SUPPORT
    areadetector_envs += "\n" + base_support
    # add AREA_DETECTOR and its modules def
    areadetector_envs += "\n" + ad_modules_def
    # add depends support path
    areadetector_envs += "\n" + depend_path
    
    areadetector_envs = areadetector_envs.format_map(epics_env_config)
    print("ad_envs:", areadetector_envs)

    # RELEASE_SUPPORT contains things in RELEASE
    # RELEASE_PRODS and RELEASE_SUPPORT are same to us
    EpicsConfig("RELEASE_SUPPORT.local", areadetector_envs)
    EpicsConfig.dump(epics_env_config, write=True)
    render_n_copy('RELEASE_LIBS.local', areadetector_envs, write=True)

    render_n_copy("CONFIG_SITE.local", 
        "\n".join([f"{K}={V}" for K,V in _external_libs.items()]),
        write=True)
