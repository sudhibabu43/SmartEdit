/*
 * Copyright 2017 The Android Open Source Project
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

#ifndef OBOE_ENGINE_OPENSLES_H
#define OBOE_ENGINE_OPENSLES_H

#include <atomic>
#include <mutex>

#include <SLES/OpenSLES.h>
#include <SLES/OpenSLES_Android.h>

namespace oboe {

/**
 * INTERNAL USE ONLY
 */
class EngineOpenSLES {
public:
  static EngineOpenSLES &getInstance();

  SLresult open();

  void close();

  SLresult createOutputMix(SLObjectItf *objectItf);

  SLresult createAudioPlayer(SLObjectItf *objectItf, SLDataSource *audioSource,
                             SLDataSink *audioSink);
  SLresult createAudioRecorder(SLObjectItf *objectItf,
                               SLDataSource *audioSource,
                               SLDataSink *audioSink);

private:
  // Make this a safe Singleton
  EngineOpenSLES() = default;
  ~EngineOpenSLES() = default;
  EngineOpenSLES(const EngineOpenSLES &) = delete;
  EngineOpenSLES &operator=(const EngineOpenSLES &) = delete;

  std::mutex mLock;
  int32_t mOpenCount = 0;

  SLObjectItf mEngineObject = nullptr;
  SLEngineItf mEngineInterface = nullptr;
};

} // namespace oboe

#endif // OBOE_ENGINE_OPENSLES_H
