/*
 * Copyright 2021 The Android Open Source Project
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

#ifndef FLOWGRAPH_MULTI_TO_MANY_CONVERTER_H
#define FLOWGRAPH_MULTI_TO_MANY_CONVERTER_H

#include <sys/types.h>
#include <unistd.h>


#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

/**
 * Convert a multi-channel interleaved stream to multiple mono-channel
 * outputs
 */
class MultiToManyConverter : public FlowGraphNode {
public:
  explicit MultiToManyConverter(int32_t channelCount);

  virtual ~MultiToManyConverter();

  int32_t onProcess(int32_t numFrames) override;

  const char *getName() override { return "MultiToManyConverter"; }

  std::vector<std::unique_ptr<flowgraph::FlowGraphPortFloatOutput>> outputs;
  flowgraph::FlowGraphPortFloatInput input;
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_MULTI_TO_MANY_CONVERTER_H
