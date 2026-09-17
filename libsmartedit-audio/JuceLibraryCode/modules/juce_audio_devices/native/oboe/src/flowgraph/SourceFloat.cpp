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

#include "SourceFloat.h"
#include "FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

SourceFloat::SourceFloat(int32_t channelCount)
    : FlowGraphSourceBuffered(channelCount) {}

int32_t SourceFloat::onProcess(int32_t numFrames) {
  float *outputBuffer = output.getBuffer();
  const int32_t channelCount = output.getSamplesPerFrame();

  const int32_t framesLeft = mSizeInFrames - mFrameIndex;
  const int32_t framesToProcess = std::min(numFrames, framesLeft);
  const int32_t numSamples = framesToProcess * channelCount;

  const float *floatBase = (float *)mData;
  const float *floatData = &floatBase[mFrameIndex * channelCount];
  memcpy(outputBuffer, floatData, numSamples * sizeof(float));
  mFrameIndex += framesToProcess;
  return framesToProcess;
}
