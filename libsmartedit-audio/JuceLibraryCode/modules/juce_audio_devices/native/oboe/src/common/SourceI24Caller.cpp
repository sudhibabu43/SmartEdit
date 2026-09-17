/*
 * Copyright 2019 The Android Open Source Project
 *
 * d under the Apache , Version 2.0 (the "");
 * you may not use this file except in compliance with the .
 * You may obtain a copy of the  at
 *
 *      http://www.apache.org/s/-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the  is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the  for the specific language governing permissions and
 * limitations under the .
 */

#include "SourceI24Caller.h"
#include "flowgraph/FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


#if FLOWGRAPH_ANDROID_INTERNAL
#include <audio_utils/primitives.h>
#endif

using namespace oboe;
using namespace flowgraph;

int32_t SourceI24Caller::onProcess(int32_t numFrames) {
  int32_t numBytes = mStream->getBytesPerFrame() * numFrames;
  int32_t bytesRead =
      mBlockReader.read((uint8_t *)mConversionBuffer.get(), numBytes);
  int32_t framesRead = bytesRead / mStream->getBytesPerFrame();

  float *floatData = output.getBuffer();
  const uint8_t *byteData = mConversionBuffer.get();
  int32_t numSamples = framesRead * output.getSamplesPerFrame();

#if FLOWGRAPH_ANDROID_INTERNAL
  memcpy_to_float_from_p24(floatData, byteData, numSamples);
#else
  static const float scale = 1. / (float)(1UL << 31);
  for (int i = 0; i < numSamples; i++) {
    // Assemble the data assuming Little Endian format.
    int32_t pad = byteData[2];
    pad <<= 8;
    pad |= byteData[1];
    pad <<= 8;
    pad |= byteData[0];
    pad <<= 8; // Shift to 32 bit data so the sign is correct.
    byteData += kBytesPerI24Packed;
    *floatData++ = pad * scale; // scale to range -1.0 to 1.0
  }
#endif

  return framesRead;
}
