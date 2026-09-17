/*
 * Copyright 2019 The Android Open Source Project
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

#include "SourceFloatCaller.h"
#include "flowgraph/FlowGraphNode.h"
#include <algorithm>
#include <unistd.h>


using namespace oboe;
using namespace flowgraph;

int32_t SourceFloatCaller::onProcess(int32_t numFrames) {
  int32_t numBytes = mStream->getBytesPerFrame() * numFrames;
  int32_t bytesRead =
      mBlockReader.read((uint8_t *)output.getBuffer(), numBytes);
  int32_t framesRead = bytesRead / mStream->getBytesPerFrame();
  return framesRead;
}
