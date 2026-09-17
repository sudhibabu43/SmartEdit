/*
 * Copyright (C) 2019 The Android Open Source Project
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

#ifndef OBOE_OBOE_FLOW_GRAPH_H
#define OBOE_OBOE_FLOW_GRAPH_H

#include <memory>
#include <stdint.h>
#include <sys/types.h>

#include "AudioSourceCaller.h"
#include "FixedBlockWriter.h"
#include <flowgraph/ChannelCountConverter.h>
#include <flowgraph/MonoToMultiConverter.h>
#include <flowgraph/MultiToMonoConverter.h>
#include <flowgraph/SampleRateConverter.h>
#include <oboe/Definitions.h>


namespace oboe {

class AudioStream;
class AudioSourceCaller;

/**
 * Convert PCM channels, format and sample rate for optimal latency.
 */
class DataConversionFlowGraph : public FixedBlockProcessor {
public:
  DataConversionFlowGraph() : mBlockWriter(*this) {}

  void setSource(const void *buffer, int32_t numFrames);

  /** Connect several modules together to convert from source to sink.
   * This should only be called once for each instance.
   *
   * @param sourceFormat
   * @param sourceChannelCount
   * @param sinkFormat
   * @param sinkChannelCount
   * @return
   */
  oboe::Result configure(oboe::AudioStream *sourceStream,
                         oboe::AudioStream *sinkStream);

  int32_t read(void *buffer, int32_t numFrames, int64_t timeoutNanos);

  int32_t write(void *buffer, int32_t numFrames);

  int32_t onProcessFixedBlock(uint8_t *buffer, int32_t numBytes) override;

  DataCallbackResult getDataCallbackResult() { return mCallbackResult; }

private:
  std::unique_ptr<flowgraph::FlowGraphSourceBuffered> mSource;
  std::unique_ptr<AudioSourceCaller> mSourceCaller;
  std::unique_ptr<flowgraph::MonoToMultiConverter> mMonoToMultiConverter;
  std::unique_ptr<flowgraph::MultiToMonoConverter> mMultiToMonoConverter;
  std::unique_ptr<flowgraph::ChannelCountConverter> mChannelCountConverter;
  std::unique_ptr<resampler::MultiChannelResampler> mResampler;
  std::unique_ptr<flowgraph::SampleRateConverter> mRateConverter;
  std::unique_ptr<flowgraph::FlowGraphSink> mSink;

  FixedBlockWriter mBlockWriter;
  DataCallbackResult mCallbackResult = DataCallbackResult::Continue;
  AudioStream *mFilterStream = nullptr;
  std::unique_ptr<uint8_t[]> mAppBuffer;
};

} // namespace oboe
#endif // OBOE_OBOE_FLOW_GRAPH_H
