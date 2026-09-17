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

#ifndef RESAMPLER_LINEAR_RESAMPLER_H
#define RESAMPLER_LINEAR_RESAMPLER_H

#include <memory>
#include <sys/types.h>
#include <unistd.h>

#include "MultiChannelResampler.h"
#include "ResamplerDefinitions.h"

namespace RESAMPLER_OUTER_NAMESPACE::resampler {

/**
 * Simple resampler that uses bi-linear interpolation.
 */
class LinearResampler : public MultiChannelResampler {
public:
  explicit LinearResampler(const MultiChannelResampler::Builder &builder);

  void writeFrame(const float *frame) override;

  void readFrame(float *frame) override;

private:
  std::unique_ptr<float[]> mPreviousFrame;
  std::unique_ptr<float[]> mCurrentFrame;
};

} /* namespace RESAMPLER_OUTER_NAMESPACE::resampler */

#endif // RESAMPLER_LINEAR_RESAMPLER_H
