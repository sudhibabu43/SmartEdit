/*
 * Copyright (C) 2017 The Android Open Source Project
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

#ifndef AAUDIO_FIXED_BLOCK_WRITER_H
#define AAUDIO_FIXED_BLOCK_WRITER_H

#include <stdint.h>

#include "FixedBlockAdapter.h"

/**
 * This can be used to convert a push data flow from variable sized buffers to
 * fixed sized buffers. An example would be an audio input callback.
 */
class FixedBlockWriter : public FixedBlockAdapter {
public:
  FixedBlockWriter(FixedBlockProcessor &fixedBlockProcessor);

  virtual ~FixedBlockWriter() = default;

  /**
   * Write from a variable sized block.
   *
   * Note that if the fixed-sized blocks must be aligned, then the
   * variable-sized blocks must have the same alignment. For example, if the
   * fixed-size blocks must be a multiple of 8, then the variable-sized blocks
   * must also be a multiple of 8.
   *
   * @param buffer
   * @param numBytes
   * @return Number of bytes written or a negative error code.
   */
  int32_t write(uint8_t *buffer, int32_t numBytes);

private:
  int32_t writeToStorage(uint8_t *buffer, int32_t numBytes);
};

#endif /* AAUDIO_FIXED_BLOCK_WRITER_H */
