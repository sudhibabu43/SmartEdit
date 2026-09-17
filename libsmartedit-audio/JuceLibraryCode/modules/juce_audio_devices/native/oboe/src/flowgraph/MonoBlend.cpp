/*
 * Copyright 2021 The Android Open Source Project
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

#include <unistd.h>

#include "MonoBlend.h"

using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

MonoBlend::MonoBlend(int32_t channelCount)
    : FlowGraphFilter(channelCount), mInvChannelCount(1. / channelCount) {}

int32_t MonoBlend::onProcess(int32_t numFrames) {
  int32_t channelCount = output.getSamplesPerFrame();
  const float *inputBuffer = input.getBuffer();
  float *outputBuffer = output.getBuffer();

  for (size_t i = 0; i < numFrames; ++i) {
    float accum = 0;
    for (size_t j = 0; j < channelCount; ++j) {
      accum += *inputBuffer++;
    }
    accum *= mInvChannelCount;
    for (size_t j = 0; j < channelCount; ++j) {
      *outputBuffer++ = accum;
    }
  }

  return numFrames;
}
