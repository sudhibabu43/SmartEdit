/*
 * Copyright 2022 The Android Open Source Project
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

#ifndef OBOE_EXTENSIONS_
#define OBOE_EXTENSIONS_

#include <stdint.h>

#include "oboe/AudioStream.h"
#include "oboe/Definitions.h"


namespace oboe {

/**
 * The definitions below are only for testing.
 * They are not recommended for use in an application.
 * They may change or be removed at any time.
 */
class OboeExtensions {
public:
  /**
   * @returns true if the device supports AAudio MMAP
   */
  static bool isMMapSupported();

  /**
   * @returns true if the AAudio MMAP data path can be selected
   */
  static bool isMMapEnabled();

  /**
   * Controls whether the AAudio MMAP data path can be selected when opening a
   * stream. It has no effect after the stream has been opened. It only affects
   * the application that calls it. Other apps are not affected.
   *
   * @param enabled
   * @return 0 or a negative error code
   */
  static int32_t setMMapEnabled(bool enabled);

  /**
   * @param oboeStream
   * @return true if the AAudio MMAP data path is used on the stream
   */
  static bool isMMapUsed(oboe::AudioStream *oboeStream);
};

} // namespace oboe

#endif // OBOE_LATENCY_TUNER_
