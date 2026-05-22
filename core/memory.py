import ctypes
import ctypes.wintypes as wintypes
from ctypes import POINTER, Structure, byref, c_size_t, c_ulong, c_void_p, sizeof, windll
import time
from typing import Optional, Tuple

processallaccess = 0x1f0fff
th32cssnapprocess = 0x00000002
th32cssnapmodule = 0x00000008
th32cssnapmodule32 = 0x00000010

class processinfo(Structure):
    _fields_ = [
        ("dwsize", wintypes.DWORD),
        ("cntusage", wintypes.DWORD),
        ("th32processid", wintypes.DWORD),
        ("th32defaultheapid", POINTER(c_ulong)),
        ("th32moduleid", wintypes.DWORD),
        ("cntthreads", wintypes.DWORD),
        ("th32parentprocessid", wintypes.DWORD),
        ("pcpriclassbase", wintypes.LONG),
        ("dwflags", wintypes.DWORD),
        ("szexefile", ctypes.c_char * 260),
    ]

class moduleinfo(Structure):
    _fields_ = [
        ("dwsize", wintypes.DWORD),
        ("th32moduleid", wintypes.DWORD),
        ("th32processid", wintypes.DWORD),
        ("glblcntusage", wintypes.DWORD),
        ("proccntusage", wintypes.DWORD),
        ("modbaseaddr", POINTER(ctypes.c_byte)),
        ("modbasesize", wintypes.DWORD),
        ("hmodule", wintypes.HMODULE),
        ("szmodule", ctypes.c_char * 256),
        ("szexepath", ctypes.c_char * 260),
    ]

class ntstuff:
    def __init__(self):
        self.ntdll = ctypes.WinDLL("ntdll.dll")
        self.kernel32 = windll.kernel32
        self.ntreadvirtualmemory = self.ntdll.NtReadVirtualMemory
        self.ntreadvirtualmemory.argtypes = [
            wintypes.HANDLE,
            c_void_p,
            c_void_p,
            c_size_t,
            POINTER(c_size_t),
        ]
        self.ntreadvirtualmemory.restype = ctypes.c_long
        self.ntwritevirtualmemory = self.ntdll.NtWriteVirtualMemory
        self.ntwritevirtualmemory.argtypes = [
            wintypes.HANDLE,
            c_void_p,
            c_void_p,
            c_size_t,
            POINTER(c_size_t),
        ]
        self.ntwritevirtualmemory.restype = ctypes.c_long

    def readmemory(self, handle: int, address: int, size: int) -> Optional[bytes]:
        buffer = ctypes.create_string_buffer(size)
        bytesread = c_size_t(0)
        status = self.ntreadvirtualmemory(
            handle,
            c_void_p(address),
            buffer,
            size,
            byref(bytesread),
        )
        if status == 0:
            return buffer.raw[: bytesread.value]
        return None

    def writememory(self, handle: int, address: int, data: bytes) -> bool:
        buffer = ctypes.create_string_buffer(data)
        byteswritten = c_size_t(0)
        status = self.ntwritevirtualmemory(
            handle,
            c_void_p(address),
            buffer,
            len(data),
            byref(byteswritten),
        )
        return status == 0 and byteswritten.value == len(data)

    def readint32(self, handle: int, address: int) -> Optional[int]:
        data = self.readmemory(handle, address, 4)
        if data:
            return int.from_bytes(data, "little")
        return None

    def readint64(self, handle: int, address: int) -> Optional[int]:
        data = self.readmemory(handle, address, 8)
        if data:
            return int.from_bytes(data, "little")
        return None

    def writeint32(self, handle: int, address: int, value: int) -> bool:
        return self.writememory(handle, address, value.to_bytes(4, "little", signed=True))

    def writeint64(self, handle: int, address: int, value: int) -> bool:
        return self.writememory(handle, address, value.to_bytes(8, "little"))

class gettheprocess:
    def __init__(self):
        self.kernel32 = windll.kernel32

    def findprocessbyname(self, processname: str) -> Optional[int]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(th32cssnapprocess, 0)
        if snapshot == -1:
            return None
        pe32 = processinfo()
        pe32.dwsize = sizeof(processinfo)
        if self.kernel32.Process32First(snapshot, byref(pe32)):
            while True:
                if pe32.szexefile.decode("utf-8", errors="ignore").lower() == processname.lower():
                    pid = pe32.th32processid
                    self.kernel32.CloseHandle(snapshot)
                    return pid
                if not self.kernel32.Process32Next(snapshot, byref(pe32)):
                    break
        self.kernel32.CloseHandle(snapshot)
        return None

    def getmodulebase(self, pid: int, modulename: str) -> Tuple[Optional[int], Optional[int]]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(th32cssnapmodule | th32cssnapmodule32, pid)
        if snapshot == -1:
            return None, None
        me32 = moduleinfo()
        me32.dwsize = sizeof(moduleinfo)
        if self.kernel32.Module32First(snapshot, byref(me32)):
            while True:
                if me32.szmodule.decode("utf-8", errors="ignore").lower() == modulename.lower():
                    base = ctypes.cast(me32.modbaseaddr, c_void_p).value
                    size = me32.modbasesize
                    self.kernel32.CloseHandle(snapshot)
                    return base, size
                if not self.kernel32.Module32Next(snapshot, byref(me32)):
                    break
        self.kernel32.CloseHandle(snapshot)
        return None, None

    def openprocess(self, pid: int) -> Optional[int]:
        handle = self.kernel32.OpenProcess(processallaccess, False, pid)
        if handle:
            return handle
        return None

def closehandle(handle: int) -> None:
    if handle:
        windll.kernel32.CloseHandle(handle)

class memoryman:
    def __init__(self):
        self.mem = ntstuff()
        self.procmgr = gettheprocess()

    def attachprocess(self, processname: str, modulename: str, pollinterval: float = 1.0) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        while True:
            pid = self.procmgr.findprocessbyname(processname)
            if pid:
                processhandle = self.procmgr.openprocess(pid)
                if processhandle:
                    modulebase, modulesize = self.procmgr.getmodulebase(pid, modulename)
                    if modulebase and modulesize:
                        return processhandle, modulebase, modulesize
                    closehandle(processhandle)
            time.sleep(pollinterval)

    def writeflagint(self, processhandle: int, fflagaddr: int, valueptroffset: int, value: int, structsize: int = 0xD0) -> bool:
        fflagstruct = self.mem.readmemory(processhandle, fflagaddr, structsize)
        if not fflagstruct:
            return False
        valueptr = int.from_bytes(fflagstruct[valueptroffset:valueptroffset + 8], "little")
        if not valueptr:
            return False
        return self.mem.writeint32(processhandle, valueptr, value)

    def writeflagstring(self, processhandle: int, fflagaddr: int, valueptroffset: int, value: str, structsize: int = 0xD0) -> bool:
        fflagstruct = self.mem.readmemory(processhandle, fflagaddr, structsize)
        if not fflagstruct:
            return False
        valueinst = int.from_bytes(fflagstruct[valueptroffset:valueptroffset + 8], "little")
        if not valueinst:
            return False
        bufferptr = self.mem.readint64(processhandle, valueinst)
        capacity = self.mem.readint64(processhandle, valueinst + 0x10)
        if bufferptr is None or capacity is None:
            return False
        newvaluebytes = value.encode("utf-8")
        newlen = len(newvaluebytes)
        if newlen > capacity:
            return False
        if not self.mem.writememory(processhandle, bufferptr, newvaluebytes + b"\x00"):
            return False
        return self.mem.writeint64(processhandle, valueinst + 0x8, newlen)