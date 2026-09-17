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

#include <memory.h>
#include <stdint.h>


#include "FixedBlockAdapter.h"

#include "FixedBlockReader.h"

FixedBlockReader::FixedBlockReader(FixedBlockProcessor &fixedBlockProcessor)
    : FixedBlockAdapter(fixedBlockProcessor) {
  mPosition = mSize;
}

int32_t FixedBlockReader::open(int32_t bytesPerFixedBlock) {
  int32_t result = FixedBlockAdapter::open(bytesPerFixedBlock);
  mPosition = 0;
  mValid = 0;
  return result;
}

int32_t FixedBlockReader::readFromStorage(uint8_t *buffer, int32_t numBytes) {
  int32_t bytesToRead = numBytes;
  int32_t dataAvailable = mValid - mPosition;
  if (bytesToRead > dataAvailable) {
    bytesToRead = dataAvailable;
  }
  memcpy(buffer, mStorage.get() + mPosition, bytesToRead);
  mPosition += bytesToRead;
  return bytesToRead;
}

int32_t FixedBlockReader::read(uint8_t *buffer, int32_t numBytes) {
  int32_t bytesRead;
  int32_t bytesLeft = numBytes;
  while (bytesLeft > 0) {
    if (mPosition < mValid) {
      // Use up bytes currently in storage.
      bytesRead = readFromStorage(buffer, bytesLeft);
      buffer += bytesRead;
      bytesLeft -= bytesRead;
    } else if (bytesLeft >= mSize) {
      // Nothing in storage. Read through if enough for a complete block.
      bytesRead = mFixedBlockProcessor.onProcessFixedBlock(buffer, mSize);
      if (bytesRead < 0)
        return bytesRead;
      buffer += bytesRead;
      bytesLeft -= bytesRead;
    } else {
      // Just need a partial block so we have to reload storage.
      bytesRead =
          mFixedBlockProcessor.onProcessFixedBlock(mStorage.get(), mSize);
      if (bytesRead < 0)
        return bytesRead;
      mPosition = 0;
      mValid = bytesRead;
      if (bytesRead == 0)
        break;
    }
  }
  return numBytes - bytesLeft;
}
