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

#ifndef NATIVEOBOE_FIFOCONTROLLERINDIRECT_H
#define NATIVEOBOE_FIFOCONTROLLERINDIRECT_H

#include <atomic>
#include <stdint.h>

#include "oboe/FifoControllerBase.h"

namespace oboe {

/**
 * A FifoControllerBase with counters external to the class.
 */
class FifoControllerIndirect : public FifoControllerBase {

public:
  FifoControllerIndirect(uint32_t bufferSize,
                         std::atomic<uint64_t> *readCounterAddress,
                         std::atomic<uint64_t> *writeCounterAddress);
  virtual ~FifoControllerIndirect() = default;

  virtual uint64_t getReadCounter() const override {
    return mReadCounterAddress->load(std::memory_order_acquire);
  }
  virtual void setReadCounter(uint64_t n) override {
    mReadCounterAddress->store(n, std::memory_order_release);
  }
  virtual void incrementReadCounter(uint64_t n) override {
    mReadCounterAddress->fetch_add(n, std::memory_order_acq_rel);
  }
  virtual uint64_t getWriteCounter() const override {
    return mWriteCounterAddress->load(std::memory_order_acquire);
  }
  virtual void setWriteCounter(uint64_t n) override {
    mWriteCounterAddress->store(n, std::memory_order_release);
  }
  virtual void incrementWriteCounter(uint64_t n) override {
    mWriteCounterAddress->fetch_add(n, std::memory_order_acq_rel);
  }

private:
  std::atomic<uint64_t> *mReadCounterAddress;
  std::atomic<uint64_t> *mWriteCounterAddress;
};

} // namespace oboe

#endif // NATIVEOBOE_FIFOCONTROLLERINDIRECT_H
