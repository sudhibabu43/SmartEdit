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

#ifndef AAUDIO_FIXED_BLOCK_READER_H
#define AAUDIO_FIXED_BLOCK_READER_H

#include <stdint.h>

#include "FixedBlockAdapter.h"

/**
 * Read from a fixed-size block to a variable sized block.
 *
 * This can be used to convert a pull data flow from fixed sized buffers to
 * variable sized buffers. An example would be an audio output callback that
 * reads from the app.
 */
class FixedBlockReader : public FixedBlockAdapter {
public:
  FixedBlockReader(FixedBlockProcessor &fixedBlockProcessor);

  virtual ~FixedBlockReader() = default;

  int32_t open(int32_t bytesPerFixedBlock) override;

  /**
   * Read into a variable sized block.
   *
   * Note that if the fixed-sized blocks must be aligned, then the
   * variable-sized blocks must have the same alignment. For example, if the
   * fixed-size blocks must be a multiple of 8, then the variable-sized blocks
   * must also be a multiple of 8.
   *
   * @param buffer
   * @param numBytes
   * @return Number of bytes read or a negative error code.
   */
  int32_t read(uint8_t *buffer, int32_t numBytes);

private:
  int32_t readFromStorage(uint8_t *buffer, int32_t numBytes);

  int32_t mValid = 0; // Number of valid bytes in mStorage.
};

#endif /* AAUDIO_FIXED_BLOCK_READER_H */
