"""
 @file
 @brief This file has code to generate audio waveform data structures
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

import math
import threading
import uuid
from functools import partial

import smartedit

from classes.app import get_app
from classes.logger import log
from classes.query import File, Clip
from classes.clip_utils import project_fps_fraction, video_length_to_project_frames



LEGACY_SAMPLES_PER_SECOND = 20
DEFAULT_SAMPLES_PER_SECOND = 200
SAMPLES_PER_SECOND = DEFAULT_SAMPLES_PER_SECOND




LEGACY_WAVEFORM_FORMAT = "normalized_peak_v1"
ABSOLUTE_WAVEFORM_FORMAT = "absolute_peak_v2"
WAVEFORM_FORMAT_KEY = "audio_data_format"
WAVEFORM_RMS_KEY = "audio_data_rms"
WAVEFORM_RATE_KEY = "audio_data_rate"




WAVEFORM_DISPLAY_EXPONENT = 0.5
WAVEFORM_DISPLAY_LUT_SIZE = 4096


def _build_waveform_display_lut():
    values = []
    for index in range(WAVEFORM_DISPLAY_LUT_SIZE):
        amplitude = index / float(WAVEFORM_DISPLAY_LUT_SIZE - 1)
        values.append(amplitude ** WAVEFORM_DISPLAY_EXPONENT)
    return tuple(values)


WAVEFORM_DISPLAY_LUT = _build_waveform_display_lut()


def waveform_data_format(ui_data):
    """Return the stored waveform format, defaulting old projects to legacy."""
    if not isinstance(ui_data, dict):
        return LEGACY_WAVEFORM_FORMAT
    return ui_data.get(WAVEFORM_FORMAT_KEY) or LEGACY_WAVEFORM_FORMAT


def waveform_sample_rate(ui_data):
    """Return stored waveform density, defaulting older data to 20 Hz."""
    if not isinstance(ui_data, dict):
        return LEGACY_SAMPLES_PER_SECOND
    try:
        rate = int(ui_data.get(WAVEFORM_RATE_KEY) or LEGACY_SAMPLES_PER_SECOND)
    except (TypeError, ValueError):
        rate = LEGACY_SAMPLES_PER_SECOND
    return rate if rate > 0 else LEGACY_SAMPLES_PER_SECOND


def configured_waveform_sample_rate():
    """Return the preferred density for newly generated waveform data."""
    try:
        settings = get_app().get_settings()
        rate = int(settings.get("timeline-waveform-samples-per-second"))
    except (AttributeError, TypeError, ValueError):
        rate = DEFAULT_SAMPLES_PER_SECOND
    return max(20, min(1000, rate))


def waveform_display_amplitude(amplitude, data_format):
    """Map a stored amplitude to display height without per-clip normalization."""
    try:
        amplitude = abs(float(amplitude))
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(amplitude):
        return 0.0
    if data_format != ABSOLUTE_WAVEFORM_FORMAT:
        return amplitude
    if amplitude <= 0.0:
        return 0.0
    index = min(
        WAVEFORM_DISPLAY_LUT_SIZE - 1,
        int(amplitude * (WAVEFORM_DISPLAY_LUT_SIZE - 1)),
    )
    return WAVEFORM_DISPLAY_LUT[index]


TIME_CURVE_RETRY_DELAY = 0.05
TIME_CURVE_MAX_RETRIES = 5

_waveform_retry_counts = {}


def _schedule_waveform_retry(file_id, clip_id, tid, reason=""):
    """Retry waveform generation for clips whose time curve or clip instance isn't ready."""

    attempts = _waveform_retry_counts.get(clip_id, 0)
    if attempts >= TIME_CURVE_MAX_RETRIES:
        _waveform_retry_counts.pop(clip_id, None)
        return False

    _waveform_retry_counts[clip_id] = attempts + 1

    if reason:
        log.debug(
            "Scheduling waveform retry %s/%s for clip %s (%s)",
            attempts + 1,
            TIME_CURVE_MAX_RETRIES,
            clip_id,
            reason,
        )

    timer = threading.Timer(
        TIME_CURVE_RETRY_DELAY,
        partial(get_audio_data, {file_id: [clip_id]}),
        kwargs={"transaction_id": tid},
    )
    timer.daemon = True
    timer.start()
    return True


def get_audio_data(files: dict, transaction_id=None):
    """Get a Clip object form libsmartedit, and grab audio data
        For for the given files and clips, start threads to gather audio data.

        arg1: a dict of clip_ids grouped by their file_id
    """

    for file_id in files:
        clip_list = files[file_id]

        log.info("Clip loaded, start thread")
        t = threading.Thread(target=get_waveform_thread, args=[file_id, clip_list, transaction_id], daemon=True)
        t.start()


def get_waveform_thread(file_id, clip_list, transaction_id):
    """
    For the given file ID and clip IDs, update audio data.

    arg1: file id to get the audio data of.
    arg2: list of clips to update when the audio data is ready.
    arg3: tid: transaction id to group waveform saves together
    """

    def getAudioData(file, channel=-1, tid=None):
        """
        Update the file query object with audio data (if found).
        """
        
        file_data = file.data
        file_ui_data = file_data.get("ui", {})
        file_audio_data = file_ui_data.get("audio_data", [])
        if file_audio_data and channel == -1:
            log.info("Audio Data already retrieved (or being retrieved).")
            return (
                file_audio_data,
                file_ui_data.get(WAVEFORM_RMS_KEY, []),
                waveform_data_format(file_ui_data),
                waveform_sample_rate(file_ui_data),
            )

        
        temp_clip = smartedit.Clip(file_data["path"])
        if temp_clip.Reader().info.has_audio == False:
            log.info(f"file: {file_data['path']} has no audio_data. Skipping")
            return

        
        get_app().window.WaitCursorSignal.emit(True)
        try:
            
            waveformer = smartedit.AudioWaveformer(temp_clip.Reader())
            sample_rate = configured_waveform_sample_rate()
            file_audio_data = waveformer.ExtractSamples(channel, sample_rate, False)
            samples_vectors = file_audio_data.vectors()
            max_samples_vector = samples_vectors[0]  
            rms_samples_vector = samples_vectors[1]  

            
            file_audio_data.clear()

            
            if channel == -1:
                get_app().window.timeline.fileAudioDataReady.emit(
                    file.id,
                    {"ui": {
                        "audio_data": max_samples_vector,
                        WAVEFORM_RMS_KEY: rms_samples_vector,
                        WAVEFORM_FORMAT_KEY: ABSOLUTE_WAVEFORM_FORMAT,
                        WAVEFORM_RATE_KEY: sample_rate,
                    }},
                    tid,
                )

            
            return (
                max_samples_vector,
                rms_samples_vector,
                ABSOLUTE_WAVEFORM_FORMAT,
                sample_rate,
            )
        finally:
            
            get_app().window.WaitCursorSignal.emit(False)

    
    file = File.get(id=file_id)

    
    if not file or not file.data.get("has_audio", False):
        log.info("File does not have audio. Skipping")
        return

    
    if transaction_id:
        tid = transaction_id
    else:
        tid = str(uuid.uuid4())

    
    
    file_audio_data = file.data.get("ui", {}).get("audio_data", [])
    file_ui_data = file.data.get("ui", {})
    file_audio_rms = file_ui_data.get(WAVEFORM_RMS_KEY, [])
    file_audio_format = waveform_data_format(file_ui_data)
    file_audio_rate = waveform_sample_rate(file_ui_data)
    if not file_audio_data:
        log.debug("Generating audio data for file %s" % file.id)
        
        get_app().window.timeline.fileAudioDataReady.emit(file.id, {"ui": {"audio_data": None}}, tid)
        
        waveform_result = getAudioData(file, tid=tid)
        if waveform_result:
            file_audio_data, file_audio_rms, file_audio_format, file_audio_rate = waveform_result

    if not file_audio_data:
        log.info("No audio data found. Aborting")
        return
    log.debug("Audio data found for file: %s" % file.data.get("path"))

    
    for clip_id in clip_list:
        clip = Clip.get(id=clip_id)

        if not clip:
            
            log.debug(f"No clip found for ID: {clip_id}. Skipping waveform generation.")
            continue

        
        channel_filter = int(
            clip.data.get("channel_filter", {}).get("Points", [])[0].get("co", {}).get("Y", -1)
        )

        time_points = clip.data.get("time", {}).get("Points", [])
        has_time_curve = isinstance(time_points, list) and len(time_points) > 1

        clip_instance = get_app().window.timeline_sync.timeline.GetClip(clip.id)
        if not clip_instance:
            reason = "clip not yet available in timeline"
            if _schedule_waveform_retry(file_id, clip.id, tid, reason):
                log.info(
                    "Waveform request deferred; clip %s not ready yet. Retrying soon.",
                    clip.id,
                )
            else:
                log.info("Clip not found, bailing out of waveform volume adjustments")
            continue

        time_point_count = clip_instance.time.GetCount()

        if has_time_curve and time_point_count <= 1:
            reason = "time curve not ready"
            if _schedule_waveform_retry(file_id, clip.id, tid, reason):
                log.debug(
                    "Clip %s time curve not ready, scheduling waveform retry", clip.id
                )
                continue

        _waveform_retry_counts.pop(clip.id, None)

        if channel_filter != -1:
            
            waveform_result = getAudioData(file, channel_filter, tid=tid)
            if waveform_result:
                file_audio_data, file_audio_rms, file_audio_format, file_audio_rate = waveform_result
            else:
                file_audio_data = None

        
        if not file_audio_data:
            log.info("File has no audio, so we cannot find any waveform audio data")
            continue

        
        get_app().window.timeline.clipAudioDataReady.emit(
            clip.id, {"ui": {"audio_data": None}}, tid
        )

        
        clip_audio_data = []
        clip_audio_rms = []
        info = clip_instance.info
        proj_fraction = project_fps_fraction()
        num_frames = video_length_to_project_frames(
            None,
            video_length=getattr(info, 'video_length', None),
            fps=getattr(info, 'fps', None),
            duration=getattr(info, 'duration', None),
            project_fps=proj_fraction,
        )
        if num_frames:
            num_frames = int(num_frames)
        else:
            fallback_frames = getattr(info, 'video_length', 0)
            num_frames = int(fallback_frames) if fallback_frames else 0

        
        
        
        sample_count = round(clip_instance.info.duration * file_audio_rate)

        if not num_frames or not sample_count:
            log.debug(
                "No frames or samples available for clip %s when generating waveform", clip.id
            )
            continue

        
        sample_ratio = float(sample_count / num_frames)

        
        
        file_data_len = len(file_audio_data)
        file_rms_len = len(file_audio_rms) if isinstance(file_audio_rms, (list, tuple)) else 0
        if not file_data_len:
            log.debug(
                "File audio data is empty for clip %s, skipping waveform generation",
                clip.id,
            )
            continue
        for sample_index in range(sample_count):
            frame_num = round(sample_index / sample_ratio) + 1
            volume = clip_instance.volume.GetValue(frame_num)
            source_index = sample_index
            if time_point_count > 1:
                
                
                source_index = min(
                    round(clip_instance.time.GetValue(frame_num) * sample_ratio),
                    sample_count - 1,
                )
            if file_data_len:
                source_index = min(source_index, file_data_len - 1)
            clip_audio_data.append(file_audio_data[source_index] * volume)
            if file_rms_len:
                rms_index = min(source_index, file_rms_len - 1)
                clip_audio_rms.append(file_audio_rms[rms_index] * abs(volume))

        
        get_app().window.timeline.clipAudioDataReady.emit(
            clip.id,
            {"ui": {
                "audio_data": clip_audio_data,
                WAVEFORM_RMS_KEY: clip_audio_rms,
                WAVEFORM_FORMAT_KEY: file_audio_format,
                WAVEFORM_RATE_KEY: file_audio_rate,
            }},
            tid,
        )
