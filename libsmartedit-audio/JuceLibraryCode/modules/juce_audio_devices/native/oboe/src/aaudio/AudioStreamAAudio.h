/*
 * Copyright 2016 The Android Open Source Project
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

#ifndef OBOE_STREAM_AAUDIO_H_
#define OBOE_STREAM_AAUDIO_H_

#include <atomic>
#include <mutex>
#include <shared_mutex>
#include <thread>


#include "AAudioLoader.h"
#include "oboe/AudioStream.h"
#include "oboe/AudioStreamBuilder.h"
#include "oboe/Definitions.h"
#include <common/AdpfWrapper.h>


namespace oboe {

/**
 * Implementation of OboeStream that uses AAudio.
 *
 * Do not create this class directly.
 * Use an OboeStreamBuilder to create one.
 */
class AudioStreamAAudio : public AudioStream {
public:
  AudioStreamAAudio();
  explicit AudioStreamAAudio(const AudioStreamBuilder &builder);

  virtual ~AudioStreamAAudio() = default;

  /**
   *
   * @return true if AAudio is supported on this device.
   */
  static bool isSupported();

  // These functions override methods in AudioStream.
  // See AudioStream for documentation.
  Result open() override;
  Result release() override;
  Result close() override;

  Result requestStart() override;
  Result requestPause() override;
  Result requestFlush() override;
  Result requestStop() override;

  ResultWithValue<int32_t> write(const void *buffer, int32_t numFrames,
                                 int64_t timeoutNanoseconds) override;

  ResultWithValue<int32_t> read(void *buffer, int32_t numFrames,
                                int64_t timeoutNanoseconds) override;

  ResultWithValue<int32_t>
  setBufferSizeInFrames(int32_t requestedFrames) override;
  int32_t getBufferSizeInFrames() override;
  ResultWithValue<int32_t> getXRunCount() override;
  bool isXRunCountSupported() const override { return true; }

  ResultWithValue<double> calculateLatencyMillis() override;

  Result waitForStateChange(StreamState currentState, StreamState *nextState,
                            int64_t timeoutNanoseconds) override;

  Result getTimestamp(clockid_t clockId, int64_t *framePosition,
                      int64_t *timeNanoseconds) override;

  StreamState getState() override;

  AudioApi getAudioApi() const override { return AudioApi::AAudio; }

  DataCallbackResult callOnAudioReady(AAudioStream *stream, void *audioData,
                                      int32_t numFrames);

  bool isMMapUsed();

  void closePerformanceHint() override {
    mAdpfWrapper.close();
    mAdpfOpenAttempted = false;
  }

protected:
  static void internalErrorCallback(AAudioStream *stream, void *userData,
                                    aaudio_result_t error);

  void *getUnderlyingStream() const override { return mAAudioStream.load(); }

  void updateFramesRead() override;
  void updateFramesWritten() override;

  void logUnsupportedAttributes();

  void beginPerformanceHintInCallback() override;

  void endPerformanceHintInCallback(int32_t numFrames) override;

  // set by callback (or app when idle)
  std::atomic<bool> mAdpfOpenAttempted{false};
  AdpfWrapper mAdpfWrapper;

private:
  // Must call under mLock. And stream must NOT be nullptr.
  Result requestStop_l(AAudioStream *stream);

  /**
   * Launch a thread that will stop the stream.
   */
  void launchStopThread();

private:
  std::atomic<bool> mCallbackThreadEnabled;
  std::atomic<bool> mStopThreadAllowed{false};

  // pointer to the underlying 'C' AAudio stream, valid if open, null if closed
  std::atomic<AAudioStream *> mAAudioStream{nullptr};
  std::shared_mutex mAAudioStreamLock; // to protect mAAudioStream while closing

  static AAudioLoader *mLibLoader;

  // We may not use this but it is so small that it is not worth allocating
  // dynamically.
  AudioStreamErrorCallback mDefaultErrorCallback;
};

} // namespace oboe

#endif // OBOE_STREAM_AAUDIO_H_
