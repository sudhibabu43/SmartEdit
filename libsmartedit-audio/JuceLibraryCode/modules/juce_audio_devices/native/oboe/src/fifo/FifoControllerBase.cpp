/*
 * Copyright 2015 The Android Open Source Project
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

#include <algorithm>
#include <cassert>
#include <stdint.h>

#include "oboe/FifoControllerBase.h"

namespace oboe {

FifoControllerBase::FifoControllerBase(uint32_t capacityInFrames)
    : mTotalFrames(capacityInFrames) {
  // Avoid ridiculously large buffers and the arithmetic wraparound issues that
  // can follow.
  assert(capacityInFrames <= (UINT32_MAX / 4));
}

uint32_t FifoControllerBase::getFullFramesAvailable() const {
  uint64_t writeCounter = getWriteCounter();
  uint64_t readCounter = getReadCounter();
  if (readCounter > writeCounter) {
    return 0;
  }
  uint64_t delta = writeCounter - readCounter;
  if (delta >= mTotalFrames) {
    return mTotalFrames;
  }
  // delta is now guaranteed to fit within the range of a uint32_t
  return static_cast<uint32_t>(delta);
}

uint32_t FifoControllerBase::getReadIndex() const {
  // % works with non-power of two sizes
  return static_cast<uint32_t>(getReadCounter() % mTotalFrames);
}

void FifoControllerBase::advanceReadIndex(uint32_t numFrames) {
  incrementReadCounter(numFrames);
}

uint32_t FifoControllerBase::getEmptyFramesAvailable() const {
  return static_cast<uint32_t>(mTotalFrames - getFullFramesAvailable());
}

uint32_t FifoControllerBase::getWriteIndex() const {
  // % works with non-power of two sizes
  return static_cast<uint32_t>(getWriteCounter() % mTotalFrames);
}

void FifoControllerBase::advanceWriteIndex(uint32_t numFrames) {
  incrementWriteCounter(numFrames);
}

} // namespace oboe
