/*
 * Copyright 2020 The Android Open Source Project
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

#ifndef FLOWGRAPH_SINK_I32_H
#define FLOWGRAPH_SINK_I32_H

#include <stdint.h>

#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

class SinkI32 : public FlowGraphSink {
public:
  explicit SinkI32(int32_t channelCount);
  ~SinkI32() override = default;

  int32_t read(void *data, int32_t numFrames) override;

  const char *getName() override { return "SinkI32"; }
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_SINK_I32_H
