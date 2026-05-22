# enjoy and have fun skidding

import json
import requests
import os
import sys
from collections import OrderedDict
from typing import Dict, Optional, Tuple
from core.memory import memoryman, closehandle

def getthemagicoffset():
    try:
        response = requests.get("https://npdrlaufeimrkvdnjijl.supabase.co/functions/v1/get-offsets", timeout=10) # using imtheo cuz idc
        if response.status_code == 200:
            import re
            match = re.search(r"Pointer\s*=\s*(0x[0-9a-fA-F]+)", response.text)
            if match:
                return int(match.group(1), 16)
    except:
        pass
    return 0x7ce33d8 # default you can change this 

theoffsetmagic = getthemagicoffset()

thebanner = r"""
██╗   ██╗███████╗██╗      ██████╗ ██████╗ ██╗███╗   ██╗
██║   ██║██╔════╝██║     ██╔═══██╗██╔══██╗██║████╗  ██║
██║   ██║█████╗  ██║     ██║   ██║██████╔╝██║██╔██╗ ██║
╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║██╔══██╗██║██║╚██╗██║
 ╚████╔╝ ███████╗███████╗╚██████╔╝██║  ██║██║██║ ╚████║
  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝
"""

mbasis = 0xcbf29ce484222325
mprime = 0x100000001b3
mbasisalt = 0x811c9dc5
mprimealt = 0x01000193

offfflagvalueptr = 0xc0
offmapend = 0x00
offmaplist = 0x10
offmapmask = 0x28
offentryforward = 0x08
offentrystring = 0x10
offentrygetset = 0x30
offstrbytes = 0x00
offstrsize = 0x10
offstralloc = 0x18
offstrcapacity = 0x18

nodereadsize = 64
nodestrides = [64, 72, 56, 80, 88, 96]
maxchainsteps = 128
maxchainsafety = 1000
minvalidptr = 0x10000
flagaddrlrumax = 4096

class therobbloxhacker:
    def __init__(self):
        self.memory = memoryman()
        self.mem = self.memory.mem
        self.processhandle = None
        self.modulebase = 0
        self.modulesize = 0
        self.cachedsingleton = 0
        self.hashcache: Dict[str, int] = {}
        self.lookupmetacache: Dict[str, Dict[str, int]] = {}
        self.valueptrlru: OrderedDict[str, int] = OrderedDict()
        self.cachemapidentity: Tuple[int, int, int] = (0, 0, 0)
        self.attachingandfuckingroblox()

    def cachevalueptr(self, name: str, valueptr: int) -> None:
        if not valueptr:
            return
        self.valueptrlru[name] = valueptr
        self.valueptrlru.move_to_end(name)
        while len(self.valueptrlru) > flagaddrlrumax:
            self.valueptrlru.popitem(last=False)

    def getcachedvalueptr(self, name: str) -> int:
        valueptr = self.valueptrlru.get(name)
        if valueptr:
            self.valueptrlru.move_to_end(name)
            return valueptr
        return 0

    def isvalidptr(self, ptr: int) -> bool:
        return isinstance(ptr, int) and minvalidptr <= ptr <= 0x7FFFFFFFFFFF

    def fnv1a64(self, name: str) -> int:
        cached = self.hashcache.get(name)
        if cached is not None:
            return cached

        basis = mbasis
        prime = mprime
        for byte in name.encode("utf-8", errors="ignore"):
            basis ^= byte
            basis = (basis * prime) & 0xFFFFFFFFFFFFFFFF

        self.hashcache[name] = basis
        return basis

    def invalidatelookupcaches(self, clearhash: bool = False) -> None:
        self.lookupmetacache.clear()
        self.valueptrlru.clear()
        if clearhash:
            self.hashcache.clear()

    def readentrynamebytes(self, entrydata: bytes) -> Tuple[bytes, int]:
        strdatastart = offentrystring
        strsize = int.from_bytes(
            entrydata[strdatastart + offstrsize:strdatastart + offstrsize + 8],
            "little",
        )
        if strsize <= 0 or strsize > 256:
            return b"", 0

        stralloc = int.from_bytes(
            entrydata[strdatastart + offstrcapacity:strdatastart + offstrcapacity + 8],
            "little",
        )

        if stralloc > 0xF:
            ptr = int.from_bytes(entrydata[strdatastart:strdatastart + 8], "little")
            if not self.isvalidptr(ptr):
                return b"", 0
            namebytes = self.mem.readmemory(self.processhandle, ptr, strsize)
            if not namebytes:
                return b"", 0
            return namebytes[:strsize], strsize

        return entrydata[strdatastart:strdatastart + strsize], strsize

    def readnodeentry(self, nodeptr: int) -> Optional[bytes]:
        if not self.isvalidptr(nodeptr):
            return None

        for readsize in nodestrides:
            if readsize < nodereadsize:
                continue
            entrydata = self.mem.readmemory(self.processhandle, nodeptr, readsize)
            if entrydata and len(entrydata) >= nodereadsize:
                return entrydata
        return None

    def attachingandfuckingroblox(self):
        print("[ + ] roblox not found huh looking for it ")
        self.processhandle, self.modulebase, self.modulesize = self.memory.attachprocess(
            "RobloxPlayerBeta.exe",
            "RobloxPlayerBeta.exe",
        )
        print(f"[ + ] Attached to handle: 0x{self.processhandle:X}")
        print(f"[ + ] Module Base: 0x{self.modulebase:X}")
        print(f"[ + ] Module Size: 0x{self.modulesize:X}")

    def getsingleton(self) -> int:
        if self.cachedsingleton:
            return self.cachedsingleton

        print("[ + ] reading FFlagList offset")
        addr = self.modulebase + theoffsetmagic
        
        absolute = self.mem.readint64(self.processhandle, addr)
        
        if absolute and absolute > 0:
            self.cachedsingleton = absolute
            print(f"[ + ] Singleton (FFlagList) found at: 0x{absolute:X} (from offset 0x{theoffsetmagic:X})")
            return absolute
        
        print("[ - ] Failed to read FFlagList rip .")
        return 0

    def whereistheflagat(self, name: str) -> int:
        valueptr = self.getcachedvalueptr(name)
        if valueptr:
            return valueptr

        singleton = self.getsingleton()
        if not singleton:
            return 0

        namebytes = name.encode("utf-8")
        hashmapaddr = singleton + 8

        mapbytes = self.mem.readmemory(self.processhandle, hashmapaddr, 56)
        if not mapbytes:
            return 0

        mapend = int.from_bytes(mapbytes[offmapend:offmapend+8], 'little')
        maplist = int.from_bytes(mapbytes[offmaplist:offmaplist+8], 'little')
        mapmask = int.from_bytes(mapbytes[offmapmask:offmapmask+8], 'little')
        mapidentity = (maplist, mapend, mapmask)

        if mapmask == 0 or maplist == 0 or not self.isvalidptr(maplist):
            return 0
        if mapidentity != self.cachemapidentity:
            self.invalidatelookupcaches(clearhash=False)
            self.cachemapidentity = mapidentity

        meta = self.lookupmetacache.get(name, {})
        if "bucketindex" in meta:
            bucketindex = meta["bucketindex"]
        else:
            basis = self.fnv1a64(name)
            bucketindex = basis & mapmask
        bucketindex &= mapmask
        bucketbase = maplist + (bucketindex * 16)

        bucketdata = self.mem.readmemory(self.processhandle, bucketbase, 16)
        if not bucketdata:
            return 0

        nodecurrent = int.from_bytes(bucketdata[8:16], 'little')
        if not self.isvalidptr(nodecurrent):
            return 0

        if nodecurrent == mapend:
            return 0

        cachednode = meta.get("nodeptr", 0)
        if cachednode and self.isvalidptr(cachednode):
            entrydata = self.readnodeentry(cachednode)
            if entrydata:
                entrynamebytes, entrylen = self.readentrynamebytes(entrydata)
                if entrylen == len(namebytes) and entrynamebytes == namebytes:
                    getset = int.from_bytes(entrydata[offentrygetset:offentrygetset+8], 'little')
                    if self.isvalidptr(getset):
                        self.lookupmetacache[name] = {
                            "bucketindex": bucketindex,
                            "nodeptr": cachednode,
                        }
                        self.cachevalueptr(name, getset)
                        return getset

        iterations = 0
        safe = 0
        visited = set()

        while iterations < maxchainsteps and safe < maxchainsafety:
            iterations += 1
            safe += 1
            if nodecurrent in visited:
                break
            visited.add(nodecurrent)

            entrydata = self.readnodeentry(nodecurrent)
            if not entrydata:
                break

            forward = int.from_bytes(entrydata[offentryforward:offentryforward+8], 'little')
            if forward and not self.isvalidptr(forward):
                break

            entrynamebytes, entrylen = self.readentrynamebytes(entrydata)
            if entrylen == len(namebytes) and entrynamebytes == namebytes:
                getset = int.from_bytes(entrydata[offentrygetset:offentrygetset+8], 'little')
                if self.isvalidptr(getset):
                    self.lookupmetacache[name] = {
                        "bucketindex": bucketindex,
                        "nodeptr": nodecurrent,
                    }
                    self.cachevalueptr(name, getset)
                    return getset

            if nodecurrent == forward or forward == 0:
                break

            nodecurrent = forward

        return 0

    def changesthetext(self, name: str, value: str) -> bool:
        addr = self.whereistheflagat(name)
        if not addr:
            return False

        try:
            return self.memory.writeflagstring(self.processhandle, addr, offfflagvalueptr, value)
        except Exception:
            return False

    def changesthenumber(self, name: str, value: int) -> bool:
        addr = self.whereistheflagat(name)
        if not addr:
            return False
        
        try:
            return self.memory.writeflagint(self.processhandle, addr, offfflagvalueptr, value)
        except:
            return False

    def themainfunctionlol(self, key: str) -> Tuple[str, str]:
        if key.startswith("FString"):
            return key[7:], "string"
        elif key.startswith("DFString"):
            return key[8:], "string"
        
        elif key.startswith("DFInt"):
            return key[5:], "int"
        elif key.startswith("FInt"):
            return key[4:], "int"
        elif key.startswith("DFLog"):
            return key[5:], "int"
        elif key.startswith("FLog"):
            return key[4:], "int"
        
        elif key.startswith("DFFlag"):
            return key[6:], "bool"
        elif key.startswith("FFlag"):
            return key[5:], "bool"
        
        else:
            if any(keyword in key.lower() for keyword in ['fahh']):
                return key, "bool"
            else:
                return key, "int"

    def doitnow(self, key: str, val) -> Tuple[bool, str]:
        cleanname, flagtype = self.themainfunctionlol(key)

        try:
            if flagtype == "string":
                if self.changesthetext(cleanname, str(val)):
                    return True, f"[ + ] {key} = \"{val}\""
                else:
                    return False, f"[ - ] Failed: {key}"

            elif flagtype == "int":
                try:
                    targetvalue = int(val)
                except:
                    return False, f"[ - ] Invalid int: {key}"
                
                if self.changesthenumber(cleanname, targetvalue):
                    return True, f"[ + ] {key} = {targetvalue}"
                else:
                    return False, f"[ - ] Failed: {key}"

            elif flagtype == "bool":
                if isinstance(val, bool):
                    targetvalue = 1 if val else 0
                else:
                    targetvalue = 1 if str(val).lower() == "true" else 0
                
                if self.changesthenumber(cleanname, targetvalue):
                    return True, f"[ + ] {key} = {bool(targetvalue)}"
                else:
                    return False, f"[ - ] Failed: {key}"

            else:
                return False, f"[ - ] Unknown type: {key}"
        except Exception as e:
            return False, f"[ - ] Error {key}: {str(e)}"

    def puttheflagsinthere(self, jsonpath: str):
        if not os.path.exists(jsonpath):
            print(f"[ - ] Error: File '{jsonpath}' not found!")
            return

        print(f"[ + ] Loading flags from: {jsonpath}")

        try:
            with open(jsonpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ - ] Error parsing JSON: {e}")
            return
        except Exception as e:
            print(f"[ - ] Error reading file: {e}")
            return

        totalflags = len(data)
        successful = 0
        failed = 0

        for key, val in data.items():
            success, message = self.doitnow(key, val)
            print(message)
            
            if success:
                successful += 1
            else:
                failed += 1

        print(f"Applied: {successful}/{totalflags}")

    def cleanup(self):
        self.invalidatelookupcaches(clearhash=True)
        if self.processhandle:
            closehandle(self.processhandle)

def getbasepath():
    if getattr(sys, 'frozen', False) or hasattr(sys, 'real_path'):
        return os.path.dirname(os.path.realpath(sys.executable))
    
    return os.path.dirname(os.path.abspath(__file__))

def main():
    print(thebanner)
    print("[ + ] Velorin FFlag Injector - discord.gg/F8kkN62Apk \n")

    try:
        fflags = therobbloxhacker()

        exedir = getbasepath()
        jsonpath = os.path.join(exedir, "fflags.json")

        print(f"[ + ] Looking for fflags.json in: {jsonpath}")

        if not os.path.exists(jsonpath):
            print("[ - ] Error: fflags.json not found!")
            print(f"    Please place 'fflags.json' in: {exedir}")
        else:
            print(f"[ + ] Found fflags.json")
            fflags.puttheflagsinthere(jsonpath)

        fflags.cleanup()

    except Exception as e:
        print(f"\n[ - ] poop: {e}")

    print("\n[ + ] done now press enter to exit bye bye")
    input()


if __name__ == "__main__":
    main()
