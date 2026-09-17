/*
 * Copyright 2018 The Android Open Source Project
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

#ifndef OBOE_STABILIZEDCALLBACK_H
#define OBOE_STABILIZEDCALLBACK_H

#include "oboe/AudioStream.h"
#include <cstdint>


namespace oboe {

class StabilizedCallback : public AudioStreamCallback {

public:
  explicit StabilizedCallback(AudioStreamCallback *callback);

  DataCallbackResult onAudioReady(AudioStream *oboeStream, void *audioData,
                                  int32_t numFrames) override;

  void onErrorBeforeClose(AudioStream *oboeStream, Result error) override {
    return mCallback->onErrorBeforeClose(oboeStream, error);
  }

  void onErrorAfterClose(AudioStream *oboeStream, Result error) override {

    // Reset all fields now that the stream has been closed
    mFrameCount = 0;
    mEpochTimeNanos = 0;
    mOpsPerNano = 1;
    return mCallback->onErrorAfterClose(oboeStream, error);
  }

private:
  AudioStreamCallback *mCallback = nullptr;
  int64_t mFrameCount = 0;
  int64_t mEpochTimeNanos = 0;
  double mOpsPerNano = 1;

  void generateLoad(int64_t durationNanos);
};

/**
 * cpu_relax is an architecture specific method of telling the CPU that you
 * don't want it to do much work. asm volatile keeps the compiler from
 * optimising these instructions out.
 */
#if defined(__i386__) || defined(__x86_64__)
#define cpu_relax() asm volatile("rep; nop" ::: "memory");

#elif defined(__arm__) || defined(__mips__) || defined(__riscv)
#define cpu_relax() asm volatile("" ::: "memory")

#elif defined(__aarch64__)
#define cpu_relax() asm volatile("yield" ::: "memory")

#else
#error "cpu_relax is not defined for this architecture"
#endif

} // namespace oboe

#endif // OBOE_STABILIZEDCALLBACK_H
