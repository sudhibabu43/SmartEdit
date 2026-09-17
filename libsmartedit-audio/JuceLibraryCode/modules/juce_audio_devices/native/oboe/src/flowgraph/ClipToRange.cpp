/*
 * Copyright 2015 The Android Open Source Project
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

#include "ClipToRange.h"
#include "FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

ClipToRange::ClipToRange(int32_t channelCount)
    : FlowGraphFilter(channelCount) {}

int32_t ClipToRange::onProcess(int32_t numFrames) {
  const float *inputBuffer = input.getBuffer();
  float *outputBuffer = output.getBuffer();

  int32_t numSamples = numFrames * output.getSamplesPerFrame();
  for (int32_t i = 0; i < numSamples; i++) {
    *outputBuffer++ = std::min(mMaximum, std::max(mMinimum, *inputBuffer++));
  }

  return numFrames;
}
