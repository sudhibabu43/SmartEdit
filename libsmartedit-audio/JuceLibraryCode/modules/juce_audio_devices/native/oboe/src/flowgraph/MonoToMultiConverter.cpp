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

#include "MonoToMultiConverter.h"
#include "FlowGraphNode.h"
#include <unistd.h>


using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

MonoToMultiConverter::MonoToMultiConverter(int32_t outputChannelCount)
    : input(*this, 1), output(*this, outputChannelCount) {}

int32_t MonoToMultiConverter::onProcess(int32_t numFrames) {
  const float *inputBuffer = input.getBuffer();
  float *outputBuffer = output.getBuffer();
  int32_t channelCount = output.getSamplesPerFrame();
  for (int i = 0; i < numFrames; i++) {
    // read one, write many
    float sample = *inputBuffer++;
    for (int channel = 0; channel < channelCount; channel++) {
      *outputBuffer++ = sample;
    }
  }
  return numFrames;
}
