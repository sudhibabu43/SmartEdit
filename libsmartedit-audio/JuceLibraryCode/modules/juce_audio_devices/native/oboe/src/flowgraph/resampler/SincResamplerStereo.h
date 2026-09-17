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

#ifndef RESAMPLER_SINC_RESAMPLER_STEREO_H
#define RESAMPLER_SINC_RESAMPLER_STEREO_H

#include <sys/types.h>
#include <unistd.h>

#include "ResamplerDefinitions.h"
#include "SincResampler.h"


namespace RESAMPLER_OUTER_NAMESPACE::resampler {

class SincResamplerStereo : public SincResampler {
public:
  explicit SincResamplerStereo(const MultiChannelResampler::Builder &builder);

  virtual ~SincResamplerStereo() = default;

  void writeFrame(const float *frame) override;

  void readFrame(float *frame) override;
};

} /* namespace RESAMPLER_OUTER_NAMESPACE::resampler */

#endif // RESAMPLER_SINC_RESAMPLER_STEREO_H
