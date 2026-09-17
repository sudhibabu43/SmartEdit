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

#include "LinearResampler.h"

using namespace RESAMPLER_OUTER_NAMESPACE::resampler;

LinearResampler::LinearResampler(const MultiChannelResampler::Builder &builder)
    : MultiChannelResampler(builder) {
  mPreviousFrame = std::make_unique<float[]>(getChannelCount());
  mCurrentFrame = std::make_unique<float[]>(getChannelCount());
}

void LinearResampler::writeFrame(const float *frame) {
  memcpy(mPreviousFrame.get(), mCurrentFrame.get(),
         sizeof(float) * getChannelCount());
  memcpy(mCurrentFrame.get(), frame, sizeof(float) * getChannelCount());
}

void LinearResampler::readFrame(float *frame) {
  float *previous = mPreviousFrame.get();
  float *current = mCurrentFrame.get();
  float phase = (float)getIntegerPhase() / mDenominator;
  // iterate across samples in the frame
  for (int channel = 0; channel < getChannelCount(); channel++) {
    float f0 = *previous++;
    float f1 = *current++;
    *frame++ = f0 + (phase * (f1 - f0));
  }
}
