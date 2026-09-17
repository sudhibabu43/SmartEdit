/*
 * Copyright 2018 The Android Open Source Project
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

#include "SinkFloat.h"
#include "FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

SinkFloat::SinkFloat(int32_t channelCount) : FlowGraphSink(channelCount) {}

int32_t SinkFloat::read(void *data, int32_t numFrames) {
  float *floatData = (float *)data;
  const int32_t channelCount = input.getSamplesPerFrame();

  int32_t framesLeft = numFrames;
  while (framesLeft > 0) {
    // Run the graph and pull data through the input port.
    int32_t framesPulled = pullData(framesLeft);
    if (framesPulled <= 0) {
      break;
    }
    const float *signal = input.getBuffer();
    int32_t numSamples = framesPulled * channelCount;
    memcpy(floatData, signal, numSamples * sizeof(float));
    floatData += numSamples;
    framesLeft -= framesPulled;
  }
  return numFrames - framesLeft;
}
