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

#ifndef FLOWGRAPH_MONO_BLEND_H
#define FLOWGRAPH_MONO_BLEND_H

#include <sys/types.h>
#include <unistd.h>

#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

/**
 * Combine data between multiple channels so each channel is an average
 * of all channels.
 */
class MonoBlend : public FlowGraphFilter {
public:
  explicit MonoBlend(int32_t channelCount);

  virtual ~MonoBlend() = default;

  int32_t onProcess(int32_t numFrames) override;

  const char *getName() override { return "MonoBlend"; }

private:
  const float mInvChannelCount;
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_MONO_BLEND
