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

#ifndef OBOE_SOURCE_I32_CALLER_H
#define OBOE_SOURCE_I32_CALLER_H

#include <memory.h>
#include <sys/types.h>
#include <unistd.h>


#include "AudioSourceCaller.h"
#include "FixedBlockReader.h"
#include "flowgraph/FlowGraphNode.h"


namespace oboe {

/**
 * AudioSource that uses callback to get more data.
 */
class SourceI32Caller : public AudioSourceCaller {
public:
  SourceI32Caller(int32_t channelCount, int32_t framesPerCallback)
      : AudioSourceCaller(channelCount, framesPerCallback, sizeof(int32_t)) {
    mConversionBuffer = std::make_unique<int32_t[]>(
        static_cast<size_t>(channelCount) *
        static_cast<size_t>(output.getFramesPerBuffer()));
  }

  int32_t onProcess(int32_t numFrames) override;

  const char *getName() override { return "SourceI32Caller"; }

private:
  std::unique_ptr<int32_t[]> mConversionBuffer;
  static constexpr float kScale = 1.0 / (1UL << 31);
};

} // namespace oboe
#endif // OBOE_SOURCE_I32_CALLER_H
