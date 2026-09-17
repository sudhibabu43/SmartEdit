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

#include "SourceI16Caller.h"
#include "flowgraph/FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


#if FLOWGRAPH_ANDROID_INTERNAL
#include <audio_utils/primitives.h>
#endif

using namespace oboe;
using namespace flowgraph;

int32_t SourceI16Caller::onProcess(int32_t numFrames) {
  int32_t numBytes = mStream->getBytesPerFrame() * numFrames;
  int32_t bytesRead =
      mBlockReader.read((uint8_t *)mConversionBuffer.get(), numBytes);
  int32_t framesRead = bytesRead / mStream->getBytesPerFrame();

  float *floatData = output.getBuffer();
  const int16_t *shortData = mConversionBuffer.get();
  int32_t numSamples = framesRead * output.getSamplesPerFrame();

#if FLOWGRAPH_ANDROID_INTERNAL
  memcpy_to_float_from_i16(floatData, shortData, numSamples);
#else
  for (int i = 0; i < numSamples; i++) {
    *floatData++ = *shortData++ * (1.0f / 32768);
  }
#endif

  return framesRead;
}
