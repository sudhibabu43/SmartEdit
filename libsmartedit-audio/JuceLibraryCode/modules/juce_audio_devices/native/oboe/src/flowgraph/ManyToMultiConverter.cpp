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

#include <unistd.h>

#include "ManyToMultiConverter.h"

using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

ManyToMultiConverter::ManyToMultiConverter(int32_t channelCount)
    : inputs(channelCount), output(*this, channelCount) {
  for (int i = 0; i < channelCount; i++) {
    inputs[i] = std::make_unique<FlowGraphPortFloatInput>(*this, 1);
  }
}

int32_t ManyToMultiConverter::onProcess(int32_t numFrames) {
  int32_t channelCount = output.getSamplesPerFrame();

  for (int ch = 0; ch < channelCount; ch++) {
    const float *inputBuffer = inputs[ch]->getBuffer();
    float *outputBuffer = output.getBuffer() + ch;

    for (int i = 0; i < numFrames; i++) {
      // read one, write into the proper interleaved output channel
      float sample = *inputBuffer++;
      *outputBuffer = sample;
      outputBuffer += channelCount; // advance to next multichannel frame
    }
  }
  return numFrames;
}
