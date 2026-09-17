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

#include <stdint.h>

#include "FifoController.h"

namespace oboe {

FifoController::FifoController(uint32_t numFrames)
    : FifoControllerBase(numFrames) {
  setReadCounter(0);
  setWriteCounter(0);
}

} // namespace oboe
