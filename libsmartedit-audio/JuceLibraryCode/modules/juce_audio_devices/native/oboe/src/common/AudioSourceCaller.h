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

#ifndef OBOE_AUDIO_SOURCE_CALLER_H
#define OBOE_AUDIO_SOURCE_CALLER_H

#include "OboeDebug.h"
#include "oboe/Oboe.h"

#include "FixedBlockReader.h"
#include "flowgraph/FlowGraphNode.h"


namespace oboe {

class AudioStreamCallback;
class AudioStream;

/**
 * For output streams that use a callback, call the application for more data.
 * For input streams that do not use a callback, read from the stream.
 */
class AudioSourceCaller : public flowgraph::FlowGraphSource,
                          public FixedBlockProcessor {
public:
  AudioSourceCaller(int32_t channelCount, int32_t framesPerCallback,
                    int32_t bytesPerSample)
      : FlowGraphSource(channelCount), mBlockReader(*this) {
    mBlockReader.open(channelCount * framesPerCallback * bytesPerSample);
  }

  /**
   * Set the stream to use as a source of data.
   * @param stream
   */
  void setStream(oboe::AudioStream *stream) { mStream = stream; }

  oboe::AudioStream *getStream() { return mStream; }

  /**
   * Timeout value to use when calling audioStream->read().
   * @param timeoutNanos Zero for no timeout or time in nanoseconds.
   */
  void setTimeoutNanos(int64_t timeoutNanos) { mTimeoutNanos = timeoutNanos; }

  int64_t getTimeoutNanos() const { return mTimeoutNanos; }

  /**
   * Called internally for block size adaptation.
   * @param buffer
   * @param numBytes
   * @return
   */
  int32_t onProcessFixedBlock(uint8_t *buffer, int32_t numBytes) override;

protected:
  oboe::AudioStream *mStream = nullptr;
  int64_t mTimeoutNanos = 0;

  FixedBlockReader mBlockReader;
};

} // namespace oboe
#endif // OBOE_AUDIO_SOURCE_CALLER_H
