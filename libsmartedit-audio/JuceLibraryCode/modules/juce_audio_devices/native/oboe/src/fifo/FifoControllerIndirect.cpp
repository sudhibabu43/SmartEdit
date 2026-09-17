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

#include <stdint.h>

#include "FifoControllerIndirect.h"

namespace oboe {

FifoControllerIndirect::FifoControllerIndirect(
    uint32_t numFrames, std::atomic<uint64_t> *readCounterAddress,
    std::atomic<uint64_t> *writeCounterAddress)
    : FifoControllerBase(numFrames), mReadCounterAddress(readCounterAddress),
      mWriteCounterAddress(writeCounterAddress) {}

} // namespace oboe
