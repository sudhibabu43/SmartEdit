"""
 @file
 @brief This file deals with unhandled exceptions
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public  as published by
 the Free Software Foundation, either version 3 of the , or
 (at your option) any later version.

 SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public  for more details.

 You should have received a copy of the GNU General Public 
 along with SmartEdit Library.  If not, see <http://www.gnu.org/s/>.
 """

import os
import platform

from classes import info
from classes import sentry


def tail_file(f, n, offset=None):
    """Read the end of a file (n number of lines)"""
    avg_line_length = 90
    to_read = n + (offset or 0)

    while True:
        try:
            
            f.seek(-(avg_line_length * to_read), 2)
        except IOError:
            
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            
            return lines[-to_read:offset and -offset or None]
        avg_line_length *= 2


def libsmartedit_crash_recovery():
    """Walk libsmartedit.log for the last line before this launch"""
    from classes.metrics import track_metric_error

    log_path = os.path.join(info.USER_PATH, "libsmartedit.log")
    last_log_line = ""
    last_stack_trace = ""
    found_stack = False
    log_start_counter = 0
    if not os.path.exists(log_path):
        return
    with open(log_path, "rb") as f:
        
        for raw_line in reversed(tail_file(f, 500)):
            
            line = " ".join(str(raw_line, 'utf-8').split()) + "\n"
            
            if "End of Stack Trace" in line:
                found_stack = True
                continue
            if "Unhandled Exception: Stack Trace" in line:
                found_stack = False
                continue
            if "libsmartedit logging:" in line:
                log_start_counter += 1
                if log_start_counter > 1:
                    
                    break

            if found_stack:
                
                last_stack_trace = line + last_stack_trace

            
            line.strip()
            if all(["---" not in line,
                    "libsmartedit logging:" not in line,
                    not last_log_line,
                    ]):
                last_log_line = line

    
    if last_stack_trace:
        
        exception_lines = last_stack_trace.split("\n")
        last_log_line = exception_lines[0].strip()

        
        
        sentry.set_context("libsmartedit", {"stack-trace": exception_lines})
        sentry.set_tag("component", "libsmartedit")

    
    if last_log_line:
        
        if platform.system() == "Darwin":
            last_log_line = "mac-%s" % last_log_line[58:].strip()
        elif platform.system() == "Windows":
            last_log_line = "windows-%s" % last_log_line
        elif platform.system() == "Linux":
            last_log_line = "linux-%s" % last_log_line.replace("/usr/local/lib/", "")

        
        last_log_line = last_log_line.replace("()", "")
        log_parts = last_log_line.split("(")
        if len(log_parts) == 2:
            last_log_line = "-%s" % log_parts[0].replace(
                "logger_libsmartedit:INFO ", "").strip()[:64]
        elif len(log_parts) >= 3:
            last_log_line = "-%s (%s" % (log_parts[0].replace(
                "logger_libsmartedit:INFO ", "").strip()[:64], log_parts[1])
    else:
        last_log_line = ""

    
    track_metric_error("unhandled-crash%s" % last_log_line, True)

    return last_log_line
