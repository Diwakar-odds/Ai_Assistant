"""
Pulsar Host - Win32 Job Object Lifecycle Manager

Uses Windows Job Objects with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE to guarantee
that all child processes (Core, Audio Worker, etc.) are terminated instantly
by the OS kernel if the Host process crashes, exits, or is killed in Task Manager.
"""

import os
import sys
import logging
import ctypes
from typing import Optional

logger = logging.getLogger("pulsar.host.job_object")

# Win32 Constants
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9

PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001


if sys.platform == "win32":
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoCounters", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryLimit", ctypes.c_size_t),
            ("PeakJobMemoryLimit", ctypes.c_size_t),
        ]


class Win32JobObject:
    """Encapsulates a Win32 Job Object configured to terminate members on close."""

    def __init__(self, name: Optional[str] = None):
        self._handle = None
        self._is_windows = sys.platform == "win32"
        if not self._is_windows:
            logger.info("[JobObject] Non-Windows OS detected; Win32 Job Object inactive.")
            return

        self._kernel32 = ctypes.windll.kernel32
        # Create Job Object
        self._handle = self._kernel32.CreateJobObjectW(None, name)
        if not self._handle:
            err = self._kernel32.GetLastError()
            raise OSError(f"Failed to create Win32 Job Object (Error: {err})")

        # Configure JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

        res = self._kernel32.SetInformationJobObject(
            self._handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not res:
            err = self._kernel32.GetLastError()
            self.close()
            raise OSError(f"Failed to set KILL_ON_JOB_CLOSE on Job Object (Error: {err})")

        logger.info(f"[JobObject] Created Win32 Job Object (Handle: {self._handle}) with KILL_ON_JOB_CLOSE.")

    @property
    def handle(self):
        return self._handle

    def assign_process(self, pid_or_handle) -> bool:
        """Assigns a process (by handle or PID) to this Job Object."""
        if not self._is_windows or not self._handle:
            return False

        # If integer PID provided
        h_process = None
        need_close_handle = False
        try:
            if isinstance(pid_or_handle, int):
                h_process = self._kernel32.OpenProcess(
                    PROCESS_SET_QUOTA | PROCESS_TERMINATE,
                    False,
                    pid_or_handle,
                )
                if not h_process:
                    err = self._kernel32.GetLastError()
                    logger.error(f"[JobObject] Failed to OpenProcess PID {pid_or_handle} (Error: {err})")
                    return False
                need_close_handle = True
            else:
                h_process = pid_or_handle

            res = self._kernel32.AssignProcessToJobObject(self._handle, h_process)
            if not res:
                err = self._kernel32.GetLastError()
                # Error 5 (ERROR_ACCESS_DENIED) indicates the child process already inherited the job object from parent
                if err == 5:
                    logger.debug(f"[JobObject] Process {pid_or_handle} already member of Job Object (inherited).")
                    return True
                logger.error(f"[JobObject] Failed to assign process to Job Object (Error: {err})")
                return False

            logger.info(f"[JobObject] Successfully assigned process PID/Handle {pid_or_handle} to Job Object.")
            return True
        finally:
            if need_close_handle and h_process:
                self._kernel32.CloseHandle(h_process)

    def close(self):
        """Closes the Job Object handle. The OS kernel will terminate all assigned processes."""
        if self._is_windows and self._handle:
            logger.info(f"[JobObject] Closing handle {self._handle}. OS kernel terminating children...")
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
