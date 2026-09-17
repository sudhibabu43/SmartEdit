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

#ifndef FLOWGRAPH_UTILITIES_H
#define FLOWGRAPH_UTILITIES_H

#include <unistd.h>

using namespace FLOWGRAPH_OUTER_NAMESPACE::flowgraph;

class FlowgraphUtilities {
public:
  // This was copied from audio_utils/primitives.h
  /**
   * Convert a single-precision floating point value to a Q0.31 integer value.
   * Rounds to nearest, ties away from 0.
   *
   * Values outside the range [-1.0, 1.0) are properly clamped to -2147483648
   * and 2147483647, including -Inf and +Inf. NaN values are considered
   * undefined, and behavior may change depending on hardware and future
   * implementation of this function.
   */
  static int32_t clamp32FromFloat(float f) {
    static const float scale = (float)(1UL << 31);
    static const float limpos = 1.;
    static const float limneg = -1.;

    if (f <= limneg) {
      return INT32_MIN;
    } else if (f >= limpos) {
      return INT32_MAX;
    }
    f *= scale;
    /* integer conversion is through truncation (though int to float is not).
     * ensure that we round to nearest, ties away from 0.
     */
    return f > 0 ? f + 0.5 : f - 0.5;
  }
};

#endif // FLOWGRAPH_UTILITIES_H
