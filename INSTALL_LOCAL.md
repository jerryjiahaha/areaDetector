1. install epics 7
2. install system depedencis (for Archlinux/Manjaro `sudo ./system_dependency.pacman.sh`)
3. check and run `config_site.py`
4. may add more configurations (*tip*: check CI files like .travis.yml in repo)
5. `make`

You can write `config_site_local.py` to setup env in `config_site.py`

env can be overrided in `config_site_local.py`:
- `epics_env_config`: `{<k>: <v>}` with env
- `depend_path`: `<LIB>=$(SUPPORT)/<lib>` areaDetector depedencies (ASYN,CALC,SNCSEQ,etc) location
- `ad_modules`: a list/tuple with areaDetector modules to build
- `external_libs`: keywords like xml2,zlib,tiff,etc

##TODO
- Use CMake to generate configurations
