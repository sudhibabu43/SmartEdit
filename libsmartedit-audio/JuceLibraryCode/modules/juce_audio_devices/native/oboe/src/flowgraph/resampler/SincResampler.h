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

#ifndef RESAMPLER_SINC_RESAMPLER_H
#define RESAMPLER_SINC_RESAMPLER_H

#include <memory>
#include <sys/types.h>
#include <unistd.h>

#include "MultiChannelResampler.h"
#include "ResamplerDefinitions.h"

namespace RESAMPLER_OUTER_NAMESPACE::resampler {

/**
 * Resampler that can interpolate between coefficients.
 * This can be used to support arbitrary ratios.
 */
class SincResampler : public MultiChannelResampler {
public:
  explicit SincResampler(const MultiChannelResampler::Builder &builder);

  virtual ~SincResampler() = default;

  void readFrame(float *frame) override;

protected:
  std::vector<float> mSingleFrame2; // for interpolation
  int32_t mNumRows = 0;
  double mPhaseScaler = 1.0;
};

} /* namespace RESAMPLER_OUTER_NAMESPACE::resampler */

#endif // RESAMPLER_SINC_RESAMPLER_H
