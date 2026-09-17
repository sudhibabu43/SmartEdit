/*
 * Copyright 2018 The Android Open Source Project
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

#ifndef FLOWGRAPH_SOURCE_I16_H
#define FLOWGRAPH_SOURCE_I16_H

#include <sys/types.h>
#include <unistd.h>


#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {
/**
 * AudioSource that reads a block of pre-defined 16-bit integer data.
 */
class SourceI16 : public FlowGraphSourceBuffered {
public:
  explicit SourceI16(int32_t channelCount);

  int32_t onProcess(int32_t numFrames) override;

  const char *getName() override { return "SourceI16"; }
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_SOURCE_I16_H
