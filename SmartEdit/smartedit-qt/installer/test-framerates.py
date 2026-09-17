"""
 @file
 @brief Utility to determine which sample rates divide evenly by which frame rates
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2020 SmartEdit Studios, LLC
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
import math
import smartedit
from src.classes import info

# Try to get the security-patched XML functions from defusedxml
try:
  from defusedxml import minidom as xml
except ImportError:
  from xml.dom import minidom as xml


all_fps = []
all_rates = [8000.0, 11025.0, 16000.0, 22050.0, 44100.0, 48000.0,
             88200.0, 96000.0, 176400.0, 192000.0, 3528000.0, 384000.0]

# Loop through all profiles (include any FPS used in SmartEdit)
for file in os.listdir(info.PROFILES_PATH):
    filepath = os.path.join(info.PROFILES_PATH, file)
    profile = smartedit.Profile(filepath)
    fps_num = profile.info.fps.num
    fps_den = profile.info.fps.den
    fps = float(fps_num) / float(fps_den)
    if fps not in all_fps:
        all_fps.append(fps)

# Loop through all export presets (include any sample rates used in SmartEdit)
for file in os.listdir(info.EXPORT_PRESETS_PATH):
    filepath = os.path.join(info.EXPORT_PRESETS_PATH, file)
    xmldoc = xml.parse(filepath)
    sampleRate = float(xmldoc.getElementsByTagName("samplerate")[0].childNodes[0].nodeValue)
    if sampleRate not in all_rates:
        all_rates.append(sampleRate)

# Display all common fps and sample rates
print("---------------------------------")
print("Common Sample Rates / Common FPS")
print("---------------------------------")
print("FPS: %s" % sorted(all_fps))
print("Sample Rates: %s" % sorted(all_rates))
print("---------------------------------")
print("GOOD = Sample rate evenly divisible by frame rate")
print("BAD = Sample rate NOT evenly divisible by frame rate")
print("---------------------------------\n")

print("(Sample Rate / FPS) = Samples Per Frame")
print("---------------------------------")
for fps in sorted(all_fps):
    for rate in sorted(all_rates):
        samples_per_frame = rate / fps
        has_remainder = math.fmod(rate, fps)
        if not has_remainder:
            # Print good case with rounding to 2 digits
            print("GOOD:\t%s / %.2f =\t%d" % (rate, fps, samples_per_frame))
        else:
            # Print bad case, without rounding the samples per frame
            print("BAD:\t%s / %.2f =\t%s.%s" %
                  (rate, fps, str(samples_per_frame).split('.')[0], str(samples_per_frame).split('.')[1][:2]))
