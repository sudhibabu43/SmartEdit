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

#ifndef FLOWGRAPH_SAMPLE_RATE_CONVERTER_H
#define FLOWGRAPH_SAMPLE_RATE_CONVERTER_H

#include <sys/types.h>
#include <unistd.h>


#include "FlowGraphNode.h"
#include "resampler/MultiChannelResampler.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

class SampleRateConverter : public FlowGraphFilter {
public:
  explicit SampleRateConverter(int32_t channelCount,
                               resampler::MultiChannelResampler &mResampler);

  virtual ~SampleRateConverter() = default;

  int32_t onProcess(int32_t numFrames) override;

  const char *getName() override { return "SampleRateConverter"; }

  void reset() override;

private:
  // Return true if there is a sample available.
  bool isInputAvailable();

  // This assumes data is available. Only call after calling isInputAvailable().
  const float *getNextInputFrame();

  resampler::MultiChannelResampler &mResampler;

  int32_t mInputCursor = 0; // offset into the input port buffer
  int32_t mNumValidInputFrames =
      0; // number of valid frames currently in the input port buffer
  // We need our own callCount for upstream calls because calls occur at a
  // different rate. This means we cannot have cyclic graphs or merges that
  // contain an SRC.
  int64_t mInputCallCount = 0;
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_SAMPLE_RATE_CONVERTER_H
