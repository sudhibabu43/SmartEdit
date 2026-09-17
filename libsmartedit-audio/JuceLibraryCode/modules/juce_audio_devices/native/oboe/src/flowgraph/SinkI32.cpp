/*
 * Copyright 2020 The Android Open Source Project
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

#include "SinkI32.h"
#include "FlowGraphNode.h"
#include "FlowgraphUtilities.h"


#if FLOWGRAPH_ANDROID_INTERNAL
#include <audio_utils/primitives.h>
#endif

using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

SinkI32::SinkI32(int32_t channelCount) : FlowGraphSink(channelCount) {}

int32_t SinkI32::read(void *data, int32_t numFrames) {
  int32_t *intData = (int32_t *)data;
  const int32_t channelCount = input.getSamplesPerFrame();

  int32_t framesLeft = numFrames;
  while (framesLeft > 0) {
    // Run the graph and pull data through the input port.
    int32_t framesRead = pullData(framesLeft);
    if (framesRead <= 0) {
      break;
    }
    const float *signal = input.getBuffer();
    int32_t numSamples = framesRead * channelCount;
#if FLOWGRAPH_ANDROID_INTERNAL
    memcpy_to_i32_from_float(intData, signal, numSamples);
    intData += numSamples;
    signal += numSamples;
#else
    for (int i = 0; i < numSamples; i++) {
      *intData++ = FlowgraphUtilities::clamp32FromFloat(*signal++);
    }
#endif
    framesLeft -= framesRead;
  }
  return numFrames - framesLeft;
}
