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

#include "PolyphaseResamplerMono.h"
#include <cassert>


using namespace RESAMPLER_OUTER_NAMESPACE::resampler;

#define MONO 1

PolyphaseResamplerMono::PolyphaseResamplerMono(
    const MultiChannelResampler::Builder &builder)
    : PolyphaseResampler(builder) {
  assert(builder.getChannelCount() == MONO);
}

void PolyphaseResamplerMono::writeFrame(const float *frame) {
  // Move cursor before write so that cursor points to last written frame in
  // read.
  if (--mCursor < 0) {
    mCursor = getNumTaps() - 1;
  }
  float *dest = &mX[mCursor * MONO];
  const int offset = mNumTaps * MONO;
  // Write each channel twice so we avoid having to wrap when running the FIR.
  const float sample = frame[0];
  // Put ordered writes together.
  dest[0] = sample;
  dest[offset] = sample;
}

void PolyphaseResamplerMono::readFrame(float *frame) {
  // Clear accumulator.
  float sum = 0.0;

  // Multiply input times precomputed windowed sinc function.
  const float *coefficients = &mCoefficients[mCoefficientCursor];
  float *xFrame = &mX[mCursor * MONO];
  const int numLoops = mNumTaps >> 2; // n/4
  for (int i = 0; i < numLoops; i++) {
    // Manual loop unrolling, might get converted to SIMD.
    sum += *xFrame++ * *coefficients++;
    sum += *xFrame++ * *coefficients++;
    sum += *xFrame++ * *coefficients++;
    sum += *xFrame++ * *coefficients++;
  }

  mCoefficientCursor = (mCoefficientCursor + mNumTaps) % mCoefficients.size();

  // Copy accumulator to output.
  frame[0] = sum;
}
