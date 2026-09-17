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

#ifndef FLOWGRAPH_MANY_TO_MULTI_CONVERTER_H
#define FLOWGRAPH_MANY_TO_MULTI_CONVERTER_H

#include <sys/types.h>
#include <unistd.h>
#include <vector>


#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

/**
 * Combine multiple mono inputs into one interleaved multi-channel output.
 */
class ManyToMultiConverter : public flowgraph::FlowGraphNode {
public:
  explicit ManyToMultiConverter(int32_t channelCount);

  virtual ~ManyToMultiConverter() = default;

  int32_t onProcess(int numFrames) override;

  void setEnabled(bool /*enabled*/) {}

  std::vector<std::unique_ptr<flowgraph::FlowGraphPortFloatInput>> inputs;
  flowgraph::FlowGraphPortFloatOutput output;

  const char *getName() override { return "ManyToMultiConverter"; }

private:
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_MANY_TO_MULTI_CONVERTER_H
