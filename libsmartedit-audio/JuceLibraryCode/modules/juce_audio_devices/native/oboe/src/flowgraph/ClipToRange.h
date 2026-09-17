/*
 * Copyright 2015 The Android Open Source Project
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

#ifndef FLOWGRAPH_CLIP_TO_RANGE_H
#define FLOWGRAPH_CLIP_TO_RANGE_H

#include <atomic>
#include <sys/types.h>
#include <unistd.h>


#include "FlowGraphNode.h"

namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph {

// This is 3 dB, (10^(3/20)), to match the maximum headroom in AudioTrack for
// float data. It is designed to allow occasional transient peaks.
constexpr float kDefaultMaxHeadroom = 1.41253754f;
constexpr float kDefaultMinHeadroom = -kDefaultMaxHeadroom;

class ClipToRange : public FlowGraphFilter {
public:
  explicit ClipToRange(int32_t channelCount);

  virtual ~ClipToRange() = default;

  int32_t onProcess(int32_t numFrames) override;

  void setMinimum(float min) { mMinimum = min; }

  float getMinimum() const { return mMinimum; }

  void setMaximum(float min) { mMaximum = min; }

  float getMaximum() const { return mMaximum; }

  const char *getName() override { return "ClipToRange"; }

private:
  float mMinimum = kDefaultMinHeadroom;
  float mMaximum = kDefaultMaxHeadroom;
};

} /* namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph */

#endif // FLOWGRAPH_CLIP_TO_RANGE_H
