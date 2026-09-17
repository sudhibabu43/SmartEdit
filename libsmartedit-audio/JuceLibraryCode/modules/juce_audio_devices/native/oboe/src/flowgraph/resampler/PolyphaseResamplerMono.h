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

#ifndef RESAMPLER_POLYPHASE_RESAMPLER_MONO_H
#define RESAMPLER_POLYPHASE_RESAMPLER_MONO_H

#include <sys/types.h>
#include <unistd.h>

#include "PolyphaseResampler.h"
#include "ResamplerDefinitions.h"

namespace RESAMPLER_OUTER_NAMESPACE::resampler {

class PolyphaseResamplerMono : public PolyphaseResampler {
public:
  explicit PolyphaseResamplerMono(
      const MultiChannelResampler::Builder &builder);

  virtual ~PolyphaseResamplerMono() = default;

  void writeFrame(const float *frame) override;

  void readFrame(float *frame) override;
};

} /* namespace RESAMPLER_OUTER_NAMESPACE::resampler */

#endif // RESAMPLER_POLYPHASE_RESAMPLER_MONO_H
